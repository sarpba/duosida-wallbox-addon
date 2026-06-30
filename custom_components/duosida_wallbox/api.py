"""HTTP client for the Duosida Wallbox add-on API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

from aiohttp import ClientError, ClientSession


class DuosidaApiError(Exception):
    """Raised when the Duosida Wallbox add-on API request fails."""


@dataclass(slots=True)
class DuosidaState:
    """Current state returned by the add-on."""

    ok: bool
    data: dict[str, Any]
    error: str | None
    updated_at: float | None
    age: float | None
    duration: float | None
    last_command: dict[str, Any] | None


class DuosidaApiClient:
    """Small async client for the local add-on dashboard API."""

    def __init__(self, session: ClientSession, base_url: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/") + "/"

    async def async_get_state(self) -> DuosidaState:
        payload = await self._request("GET", "api/state")
        data = payload.get("data")
        return DuosidaState(
            ok=bool(payload.get("ok")),
            data=data if isinstance(data, dict) else {},
            error=payload.get("error") if isinstance(payload.get("error"), str) else None,
            updated_at=self._float_or_none(payload.get("updated_at")),
            age=self._float_or_none(payload.get("age")),
            duration=self._float_or_none(payload.get("duration")),
            last_command=payload.get("last_command") if isinstance(payload.get("last_command"), dict) else None,
        )

    async def async_refresh(self) -> None:
        await self._request("GET", "api/refresh")

    async def async_set_max_current(self, value: float) -> DuosidaState:
        payload = await self._request("POST", "api/config/max-current", json={"value": value})
        return self._state_from_command(payload)

    async def async_start_charging(self, id_tag: str) -> DuosidaState:
        payload = await self._request("POST", "api/charging/start", json={"id_tag": id_tag})
        return self._state_from_command(payload)

    async def async_stop_charging(self, transaction_id: int | None = None) -> DuosidaState:
        body: dict[str, Any] = {}
        if transaction_id is not None:
            body["transaction_id"] = transaction_id
        payload = await self._request("POST", "api/charging/stop", json=body)
        return self._state_from_command(payload)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = urljoin(self._base_url, path)
        try:
            async with asyncio.timeout(20):
                response = await self._session.request(method, url, **kwargs)
                payload = await response.json(content_type=None)
        except TimeoutError as exc:
            raise DuosidaApiError(f"Timed out connecting to {url}") from exc
        except (ClientError, ValueError) as exc:
            raise DuosidaApiError(f"Failed to call {url}: {exc}") from exc

        if not isinstance(payload, dict):
            raise DuosidaApiError(f"Invalid response from {url}")
        if response.status >= 400 or payload.get("ok") is False:
            raise DuosidaApiError(str(payload.get("error") or f"HTTP {response.status}"))
        return payload

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _state_from_command(payload: dict[str, Any]) -> DuosidaState:
        state = payload.get("state")
        if not isinstance(state, dict):
            raise DuosidaApiError("Command response did not include state")
        data = state.get("data")
        return DuosidaState(
            ok=bool(state.get("ok")),
            data=data if isinstance(data, dict) else {},
            error=state.get("error") if isinstance(state.get("error"), str) else None,
            updated_at=DuosidaApiClient._float_or_none(state.get("updated_at")),
            age=DuosidaApiClient._float_or_none(state.get("age")),
            duration=DuosidaApiClient._float_or_none(state.get("duration")),
            last_command=state.get("last_command") if isinstance(state.get("last_command"), dict) else None,
        )
