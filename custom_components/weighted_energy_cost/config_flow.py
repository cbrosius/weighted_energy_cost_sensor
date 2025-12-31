"""Config flow for Weighted Energy Cost Sensor integration."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_GRID_IMPORT_SOURCE_TYPE,
    CONF_GRID_IMPORT_SOURCE_VALUE,
    CONF_GRID_IMPORT_PRICE_TYPE,
    CONF_GRID_IMPORT_PRICE_VALUE,
    CONF_SOLAR_SOURCE_TYPE,
    CONF_SOLAR_SOURCE_VALUE,
    CONF_SOLAR_PRICE_TYPE,
    CONF_SOLAR_PRICE_VALUE,
    CONF_BATTERY_POWER_SOURCE_TYPE,
    CONF_BATTERY_POWER_SOURCE_VALUE,
    CONF_BATTERY_ENERGY_SOURCE_TYPE,
    CONF_BATTERY_ENERGY_SOURCE_VALUE,
    SOURCE_TYPE_ENTITY,
    SOURCE_TYPE_FIXED,
    SOURCE_TYPE_DASHBOARD,
    DEFAULT_NAME,
)


class WeightedEnergyCostConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Weighted Energy Cost Sensor."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> WeightedEnergyCostOptionsFlow:
        """Get the options flow for this handler."""
        return WeightedEnergyCostOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Name and initial setup."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_grid_import()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME, default=DEFAULT_NAME): str}
            ),
        )

    async def _async_show_type_step(
        self,
        step_id: str,
        key: str,
        allow_dashboard: bool = False,
        default=SOURCE_TYPE_ENTITY,
    ):
        options = [
            {"value": SOURCE_TYPE_ENTITY, "label": "Sensor Entity"},
            {"value": SOURCE_TYPE_FIXED, "label": "Fixed Value"},
        ]
        if allow_dashboard:
            options.append(
                {"value": SOURCE_TYPE_DASHBOARD, "label": "Energy Dashboard Entity"}
            )

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        key, default=self.data.get(key, default)
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options, mode=selector.SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
            last_step=False,
        )

    async def _async_show_value_step(self, step_id: str, type_key: str, value_key: str):
        source_type = self.data[type_key]
        current_val = self.data.get(value_key)

        if source_type == SOURCE_TYPE_FIXED:
            # Safety check: if current_val is a sensor name (str starting with sensor.), default to 0.0
            default_num = 0.0
            if current_val is not None:
                try:
                    default_num = float(current_val)
                except (ValueError, TypeError):
                    default_num = 0.0

            schema = vol.Schema(
                {
                    vol.Required(
                        value_key, default=default_num
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            mode=selector.NumberSelectorMode.BOX, step=0.001
                        )
                    )
                }
            )
        elif source_type == SOURCE_TYPE_DASHBOARD:
            schema = vol.Schema(
                {
                    vol.Required(
                        value_key,
                        default=current_val if isinstance(current_val, str) else None,
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class=SensorDeviceClass.ENERGY
                        )
                    )
                }
            )
        else:
            schema = vol.Schema(
                {
                    vol.Required(
                        value_key,
                        default=current_val if isinstance(current_val, str) else None,
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    )
                }
            )

        return self.async_show_form(
            step_id=step_id, data_schema=schema, last_step=False
        )

    async def async_step_grid_import(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_grid_import_value()
        return await self._async_show_type_step(
            "grid_import", CONF_GRID_IMPORT_SOURCE_TYPE, allow_dashboard=True
        )

    async def async_step_grid_import_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_grid_price()
        return await self._async_show_value_step(
            "grid_import_value",
            CONF_GRID_IMPORT_SOURCE_TYPE,
            CONF_GRID_IMPORT_SOURCE_VALUE,
        )

    async def async_step_grid_price(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_grid_price_value()
        return await self._async_show_type_step(
            "grid_price", CONF_GRID_IMPORT_PRICE_TYPE, default=SOURCE_TYPE_FIXED
        )

    async def async_step_grid_price_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_solar()
        return await self._async_show_value_step(
            "grid_price_value",
            CONF_GRID_IMPORT_PRICE_TYPE,
            CONF_GRID_IMPORT_PRICE_VALUE,
        )

    async def async_step_solar(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_solar_value()
        return await self._async_show_type_step(
            "solar", CONF_SOLAR_SOURCE_TYPE, allow_dashboard=True
        )

    async def async_step_solar_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_solar_price()
        return await self._async_show_value_step(
            "solar_value", CONF_SOLAR_SOURCE_TYPE, CONF_SOLAR_SOURCE_VALUE
        )

    async def async_step_solar_price(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_solar_price_value()
        return await self._async_show_type_step(
            "solar_price", CONF_SOLAR_PRICE_TYPE, default=SOURCE_TYPE_FIXED
        )

    async def async_step_solar_price_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_battery_power()
        return await self._async_show_value_step(
            "solar_price_value", CONF_SOLAR_PRICE_TYPE, CONF_SOLAR_PRICE_VALUE
        )

    async def async_step_battery_power(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_battery_power_value()
        return await self._async_show_type_step(
            "battery_power", CONF_BATTERY_POWER_SOURCE_TYPE
        )

    async def async_step_battery_power_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_battery_energy()
        return await self._async_show_value_step(
            "battery_power_value",
            CONF_BATTERY_POWER_SOURCE_TYPE,
            CONF_BATTERY_POWER_SOURCE_VALUE,
        )

    async def async_step_battery_energy(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_battery_energy_value()
        return await self._async_show_type_step(
            "battery_energy", CONF_BATTERY_ENERGY_SOURCE_TYPE
        )

    async def async_step_battery_energy_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)
        return await self._async_show_value_step(
            "battery_energy_value",
            CONF_BATTERY_ENERGY_SOURCE_TYPE,
            CONF_BATTERY_ENERGY_SOURCE_VALUE,
        )


class WeightedEnergyCostOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Weighted Energy Cost Sensor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self.data = dict(config_entry.data)
        if config_entry.options:
            self.data.update(config_entry.options)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_grid_import()

    async def _async_show_type_step(
        self, step_id, key, allow_dashboard=False, default=SOURCE_TYPE_ENTITY
    ):
        options = [
            {"value": SOURCE_TYPE_ENTITY, "label": "Sensor Entity"},
            {"value": SOURCE_TYPE_FIXED, "label": "Fixed Value"},
        ]
        if allow_dashboard:
            options.append(
                {"value": SOURCE_TYPE_DASHBOARD, "label": "Energy Dashboard Entity"}
            )

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        key, default=self.data.get(key, default)
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options, mode=selector.SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
            last_step=False,
        )

    async def _async_show_value_step(self, step_id, type_key, value_key):
        source_type = self.data[type_key]
        current_val = self.data.get(value_key)

        if source_type == SOURCE_TYPE_FIXED:
            default_num = 0.0
            if current_val is not None:
                try:
                    default_num = float(current_val)
                except (ValueError, TypeError):
                    default_num = 0.0

            schema = vol.Schema(
                {
                    vol.Required(
                        value_key, default=default_num
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            mode=selector.NumberSelectorMode.BOX, step=0.001
                        )
                    )
                }
            )
        elif source_type == SOURCE_TYPE_DASHBOARD:
            schema = vol.Schema(
                {
                    vol.Required(
                        value_key,
                        default=current_val if isinstance(current_val, str) else None,
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class=SensorDeviceClass.ENERGY
                        )
                    )
                }
            )
        else:
            schema = vol.Schema(
                {
                    vol.Required(
                        value_key,
                        default=current_val if isinstance(current_val, str) else None,
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    )
                }
            )

        return self.async_show_form(
            step_id=step_id, data_schema=schema, last_step=False
        )

    async def async_step_grid_import(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_grid_import_value()
        return await self._async_show_type_step(
            "grid_import", CONF_GRID_IMPORT_SOURCE_TYPE, allow_dashboard=True
        )

    async def async_step_grid_import_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_grid_price()
        return await self._async_show_value_step(
            "grid_import_value",
            CONF_GRID_IMPORT_SOURCE_TYPE,
            CONF_GRID_IMPORT_SOURCE_VALUE,
        )

    async def async_step_grid_price(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_grid_price_value()
        return await self._async_show_type_step(
            "grid_price", CONF_GRID_IMPORT_PRICE_TYPE, default=SOURCE_TYPE_FIXED
        )

    async def async_step_grid_price_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_solar()
        return await self._async_show_value_step(
            "grid_price_value",
            CONF_GRID_IMPORT_PRICE_TYPE,
            CONF_GRID_IMPORT_PRICE_VALUE,
        )

    async def async_step_solar(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_solar_value()
        return await self._async_show_type_step(
            "solar", CONF_SOLAR_SOURCE_TYPE, allow_dashboard=True
        )

    async def async_step_solar_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_solar_price()
        return await self._async_show_value_step(
            "solar_value", CONF_SOLAR_SOURCE_TYPE, CONF_SOLAR_SOURCE_VALUE
        )

    async def async_step_solar_price(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_solar_price_value()
        return await self._async_show_type_step(
            "solar_price", CONF_SOLAR_PRICE_TYPE, default=SOURCE_TYPE_FIXED
        )

    async def async_step_solar_price_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_battery_power()
        return await self._async_show_value_step(
            "solar_price_value", CONF_SOLAR_PRICE_TYPE, CONF_SOLAR_PRICE_VALUE
        )

    async def async_step_battery_power(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_battery_power_value()
        return await self._async_show_type_step(
            "battery_power", CONF_BATTERY_POWER_SOURCE_TYPE
        )

    async def async_step_battery_power_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_battery_energy()
        return await self._async_show_value_step(
            "battery_power_value",
            CONF_BATTERY_POWER_SOURCE_TYPE,
            CONF_BATTERY_POWER_SOURCE_VALUE,
        )

    async def async_step_battery_energy(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return await self.async_step_battery_energy_value()
        return await self._async_show_type_step(
            "battery_energy", CONF_BATTERY_ENERGY_SOURCE_TYPE
        )

    async def async_step_battery_energy_value(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return self.async_create_entry(title="", data=self.data)
        return await self._async_show_value_step(
            "battery_energy_value",
            CONF_BATTERY_ENERGY_SOURCE_TYPE,
            CONF_BATTERY_ENERGY_SOURCE_VALUE,
        )
