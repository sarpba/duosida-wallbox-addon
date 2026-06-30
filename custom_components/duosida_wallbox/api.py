"""Direct TCP client for Duosida Wallbox chargers."""

from __future__ import annotations

import asyncio
import socket
import time
from dataclasses import dataclass
from typing import Any, Callable

from . import protocol


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

    async def async_start_charging(self, id_tag: str) -> DuosidaState:
        async with self._lock:
            return await asyncio.to_thread(self._set_charging, True, id_tag, None)

    async def async_stop_charging(self, transaction_id: int | None = None) -> DuosidaState:
        async with self._lock:
            return await asyncio.to_thread(self._set_charging, False, None, transaction_id)

    def _get_state(self) -> DuosidaState:
        started = time.time()
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
            raise DuosidaApiError(f"No response from charger on TCP/{self._port}")
        self._update_client_id(data)
        return self._state(data, started)

    def _set_max_current(self, value: float) -> DuosidaState:
        started = time.time()
        value = round(float(value))
        if not 6 <= value <= 32:
            raise DuosidaApiError("Maximum current must be between 6 and 32 A")

        command_data = self._command_state(
            lambda message_id: protocol.build_change_configuration(
                self._client_id,
                message_id,
                "VendorMaxWorkCurrent",
                f"{value:g}",
            ),
            duration=max(5, min(self._probe_duration, 8)),
        )
        status = command_data.get("change_configuration_status")
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
                raise DuosidaApiError(verify_error or "Charger did not confirm configuration change")

        configured = data.get("config_maxWorkCurrent")
        if configured is not None and abs(float(configured) - value) > 0.1:
            raise DuosidaApiError(f"Charger still reports {configured} A after saving {value:g} A")
        if configured is None and status in {"Accepted", "RebootRequired"}:
            data["config_maxWorkCurrent"] = value
        if status is None:
            status = data.get("change_configuration_status") or "Verified"

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

    def _set_charging(self, enabled: bool, id_tag: str | None, transaction_id: int | None) -> DuosidaState:
        started = time.time()
        if enabled:
            command_type = "start_charging"
            command_value: object = id_tag or "HA"
            data = self._command_state(
                lambda message_id: protocol.build_remote_start(self._client_id, message_id, str(command_value)),
                duration=max(5, min(self._probe_duration, 8)),
            )
            status = data.get("remote_start_status")
        else:
            if transaction_id is None:
                transaction_id = self._last_transaction_id()
            if transaction_id is None:
                raise DuosidaApiError("Charger did not report an active transaction id")
            command_type = "stop_charging"
            command_value = transaction_id
            data = self._command_state(
                lambda message_id: protocol.build_remote_stop(self._client_id, message_id, transaction_id),
                duration=max(5, min(self._probe_duration, 8)),
            )
            status = data.get("remote_stop_status")

        if status == "Rejected":
            raise DuosidaApiError(f"Charger rejected {command_type}")

        self._update_client_id(data)
        return self._state(
            data,
            started,
            last_command={
                "type": command_type,
                "value": command_value,
                "status": status or "Sent",
                "updated_at": time.time(),
            },
        )

    def _command_state(self, payload_factory: Callable[[int], bytes], duration: int) -> dict[str, Any]:
        frames = self._recv(payload_factory(self._message_id()), duration=duration)
        data = protocol.build_state(frames)
        if not data:
            raise DuosidaApiError(f"No response from charger on TCP/{self._port}")
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

    def _last_transaction_id(self) -> int | None:
        try:
            state = self._get_state()
        except DuosidaApiError:
            return None
        value = state.data.get("transaction_id") or state.data.get("vendor_transactionId")
        if value in {None, "", 0, "0"}:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _message_id() -> int:
        return int(time.time()) & 0x7FFFFFFF
