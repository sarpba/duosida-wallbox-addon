"""Data coordinator for the Duosida Wallbox integration."""

from __future__ import annotations

from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DuosidaApiClient, DuosidaApiError, DuosidaState
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class DuosidaDataUpdateCoordinator(DataUpdateCoordinator[DuosidaState]):
    """Coordinator that polls the charger directly."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: DuosidaApiClient,
    ) -> None:
        self.client = client
        self.config_entry = config_entry
        scan_interval = config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=int(scan_interval)),
        )

    @property
    def values(self) -> dict[str, Any]:
        """Return charger data values."""
        return self.data.data if self.data else {}

    @property
    def last_error(self) -> str | None:
        """Return the latest charger communication error."""
        return self.data.error if self.data else None

    async def _async_update_data(self) -> DuosidaState:
        try:
            return await self.client.async_get_state()
        except DuosidaApiError as exc:
            if self.data is not None:
                _LOGGER.warning("Duosida poll failed, keeping previous state: %s", exc)
                return DuosidaState(
                    ok=False,
                    data=self.data.data,
                    error=str(exc),
                    updated_at=self.data.updated_at,
                    age=time.time() - self.data.updated_at if self.data.updated_at else None,
                    duration=None,
                    last_command=self.data.last_command,
                )
            raise UpdateFailed(str(exc)) from exc

    async def async_command_refresh(self) -> None:
        """Poll the charger now."""
        try:
            state = await self.client.async_refresh()
        except DuosidaApiError as exc:
            raise HomeAssistantError(str(exc)) from exc
        self.async_set_updated_data(state)

    async def async_set_max_current(self, value: float) -> None:
        """Set maximum charging current."""
        try:
            state = await self.client.async_set_max_current(value)
        except DuosidaApiError as exc:
            raise HomeAssistantError(str(exc)) from exc
        self.async_set_updated_data(self._merge_state(state))

    async def async_start_charging(self, id_tag: str) -> None:
        """Send remote start command."""
        try:
            state = await self.client.async_start_charging(id_tag)
        except DuosidaApiError as exc:
            raise HomeAssistantError(str(exc)) from exc
        self.async_set_updated_data(self._merge_state(state))

    async def async_stop_charging(self, transaction_id: int | None = None) -> None:
        """Send remote stop command."""
        try:
            state = await self.client.async_stop_charging(transaction_id)
        except DuosidaApiError as exc:
            raise HomeAssistantError(str(exc)) from exc
        self.async_set_updated_data(self._merge_state(state))

    def _merge_state(self, state: DuosidaState) -> DuosidaState:
        """Merge partial command responses into the previous state."""
        if self.data is not None:
            merged_data = dict(self.data.data)
            merged_data.update(state.data)
            return DuosidaState(
                ok=state.ok,
                data=merged_data,
                error=state.error,
                updated_at=state.updated_at,
                age=state.age,
                duration=state.duration,
                last_command=state.last_command,
            )
        return state
