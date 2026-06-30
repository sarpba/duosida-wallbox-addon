"""Direct TCP client for Duosida Wallbox chargers."""

from __future__ import annotations

import asyncio
import logging
import socket
import time
from dataclasses import dataclass
from typing import Any, Callable

from . import protocol

_LOGGER = logging.getLogger(__name__)


class DuosidaApiError(Exception):
    """Raised when communication with the charger fails."""


@dataclass(slots=True)
class DuosidaState:
    """Current charger state."""

    ok: bool
    data: dict[str, Any]
    error: str | None
    updated_at: float | None
    age: float | None
    duration: float | None
    last_command: dict[str, Any] | None


class DuosidaApiClient:
    """Async wrapper around the charger's blocking TCP protocol."""

    def __init__(
        self,
        host: str,
        port: int,
        probe_duration: int,
        client_id: str = "From Python",
        transport: str = "raw",
    ) -> None:
        self._host = host
        self._port = port
        self._probe_duration = probe_duration
        self._client_id = client_id
        self._transport = transport
        self._lock = asyncio.Lock()

    async def async_get_state(self) -> DuosidaState:
        async with self._lock:
            return await asyncio.to_thread(self._get_state)

    async def async_refresh(self) -> DuosidaState:
        return await self.async_get_state()

    async def async_set_max_current(self, value: float) -> DuosidaState:
        async with self._lock:
            return await asyncio.to_thread(self._set_max_current, value)

    def _get_state(self) -> DuosidaState:
        started = time.time()
        _LOGGER.debug(
            "Polling Duosida charger at %s:%s for up to %ss",
            self._host,
            self._port,
            self._probe_duration,
        )
        payload = protocol.build_trigger_boot(self._client_id, self._message_id())
        frames = self._recv(
            payload,
            duration=self._probe_duration,
            request_config=True,
            session_triggers=[
                protocol.TRIGGER_NAME_TO_VALUE["meter-values"],
                protocol.TRIGGER_NAME_TO_VALUE["status"],
            ],
        )
        data = protocol.build_state(frames)
        if not data:
            _LOGGER.debug("Duosida poll finished with %s frames but no decoded state", len(frames))
            raise DuosidaApiError(f"No response from charger on TCP/{self._port}")
        self._update_client_id(data)
        _LOGGER.debug(
            "Duosida poll finished in %.2fs with %s frames and keys: %s",
            time.time() - started,
            len(frames),
            sorted(data),
        )
        return self._state(data, started)

    def _set_max_current(self, value: float) -> DuosidaState:
        started = time.time()
        value = round(float(value))
        if not 6 <= value <= 32:
            raise DuosidaApiError("Maximum current must be between 6 and 32 A")

        _LOGGER.debug("Setting Duosida max current to %s A", value)
        command_data = self._command_state(
            lambda message_id: protocol.build_change_configuration(
                self._client_id,
                message_id,
                "VendorMaxWorkCurrent",
                f"{value:g}",
            ),
            duration=max(5, min(self._probe_duration, 8)),
            require_state=False,
        )
        status = command_data.get("change_configuration_status")
        _LOGGER.debug("Duosida max current command status: %s", status)
        if status in {"Rejected", "NotSupported"}:
            raise DuosidaApiError(f"Charger rejected configuration change: {status}")

        verify_error: str | None = None
        data: dict[str, Any] = {}
        for attempt in range(2):
            if attempt:
                time.sleep(1.5)
            try:
                data = self._command_state(
                    lambda message_id: protocol.build_pull_config(self._client_id, message_id),
                    duration=max(self._probe_duration, 8),
                )
            except DuosidaApiError as exc:
                verify_error = str(exc)
                continue
            if data.get("config_maxWorkCurrent") is not None:
                break

        if not data:
            if status in {"Accepted", "RebootRequired"}:
                data = command_data
            else:
                _LOGGER.warning(
                    "Duosida max current verification failed after command status %s; keeping requested value "
                    "optimistically. Last verification error: %s",
                    status or "unknown",
                    verify_error,
                )
                data = dict(command_data)
                data["config_maxWorkCurrent"] = value

        configured = data.get("config_maxWorkCurrent")
        _LOGGER.debug("Duosida max current verification reported: %s A", configured)
        if configured is not None and abs(float(configured) - value) > 0.1:
            raise DuosidaApiError(f"Charger still reports {configured} A after saving {value:g} A")
        if configured is None and status in {"Accepted", "RebootRequired"}:
            data["config_maxWorkCurrent"] = value
        if status is None:
            status = data.get("change_configuration_status") or "Sent"

        self._update_client_id(data)
        return self._state(
            data,
            started,
            last_command={
                "type": "set_max_current",
                "value": value,
                "status": status,
                "updated_at": time.time(),
            },
        )

    def _command_state(
        self,
        payload_factory: Callable[[int], bytes],
        duration: int,
        require_state: bool = True,
    ) -> dict[str, Any]:
        _LOGGER.debug("Sending Duosida command and waiting up to %ss", duration)
        frames = self._recv(payload_factory(self._message_id()), duration=duration)
        data = protocol.build_state(frames)
        if not data:
            _LOGGER.debug("Duosida command finished with %s frames but no decoded state", len(frames))
            if not require_state:
                return {}
            raise DuosidaApiError(f"No response from charger on TCP/{self._port}")
        _LOGGER.debug("Duosida command returned keys: %s", sorted(data))
        return data

    def _recv(
        self,
        payload: bytes,
        duration: int,
        request_config: bool = False,
        session_triggers: list[int] | None = None,
    ) -> list[bytes]:
        try:
            return protocol.recv_frames(
                self._host,
                self._port,
                protocol.maybe_wrap(payload, self._transport),
                duration,
                transport=self._transport,
                request_config=request_config,
                session_triggers=session_triggers or [],
                config_updates=[],
                persist_config=True,
            )
        except (OSError, socket.timeout) as exc:
            raise DuosidaApiError(f"Cannot connect to charger {self._host}:{self._port}: {exc}") from exc

    def _state(
        self,
        data: dict[str, Any],
        started: float,
        last_command: dict[str, Any] | None = None,
    ) -> DuosidaState:
        return DuosidaState(
            ok=True,
            data=data,
            error=None,
            updated_at=time.time(),
            age=0,
            duration=round(time.time() - started, 2),
            last_command=last_command,
        )

    def _update_client_id(self, data: dict[str, Any]) -> None:
        client_id = data.get("client_id") or data.get("chargePointSerialNumber")
        if client_id:
            self._client_id = str(client_id)

    @staticmethod
    def _message_id() -> int:
        return int(time.time()) & 0x7FFFFFFF
