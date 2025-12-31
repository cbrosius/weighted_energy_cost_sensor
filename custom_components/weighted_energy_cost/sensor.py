"""Sensor platform for Weighted Energy Cost Sensor."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

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
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities([WeightedEnergyCostSensor(hass, entry)])


class WeightedEnergyCostSensor(RestoreEntity, SensorEntity):
    """Representation of a Weighted Energy Cost Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:currency-eur"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self._attr_name = entry.data.get(CONF_NAME)
        self._attr_unique_id = f"{entry.entry_id}_weighted_cost"
        self._attr_native_unit_of_measurement = "€/kWh"

        self._state = 0.0
        self._total_battery_cost = 0.0
        self._last_update = None

        # Track previous energy values for rate calculation
        self._last_energy_values: dict[str, float] = {}

        self._entities_to_track = []
        self._setup_entities()

    def _setup_entities(self):
        """Identify which entities to track."""
        for key in [
            CONF_GRID_IMPORT_SOURCE_VALUE,
            CONF_GRID_IMPORT_PRICE_VALUE,
            CONF_SOLAR_SOURCE_VALUE,
            CONF_SOLAR_PRICE_VALUE,
            CONF_BATTERY_POWER_SOURCE_VALUE,
            CONF_BATTERY_ENERGY_SOURCE_VALUE,
        ]:
            val = self.entry.data.get(key)
            if val and isinstance(val, str) and "." in val:
                self._entities_to_track.append(val)

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        if (old_state := await self.async_get_last_state()) is not None:
            try:
                self._state = (
                    float(old_state.state)
                    if old_state.state not in ["unknown", "unavailable"]
                    else 0.0
                )
                self._total_battery_cost = float(
                    old_state.attributes.get("total_battery_cost", 0.0)
                )
            except (ValueError, TypeError):
                self._total_battery_cost = 0.0

        self._last_update = datetime.now()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._entities_to_track, self._handle_state_change
            )
        )
        self._update_values_and_calculate()

    @callback
    def _handle_state_change(self, event):
        """Handle tracked entity state change."""
        self._update_values_and_calculate()

    def _get_kw_value(self, type_key, value_key, dt_hours):
        """Get value and normalize to kW."""
        t = self.entry.data.get(type_key)
        v = self.entry.data.get(value_key)

        if t == SOURCE_TYPE_FIXED:
            try:
                # For fixed values, we assume it's kW if small, W if > 10.
                val = float(v)
                return val / 1000.0 if val > 10 else val
            except (ValueError, TypeError):
                return 0.0

        state = self.hass.states.get(v)
        if not state or state.state in ["unknown", "unavailable"]:
            return 0.0

        try:
            val = float(state.state)
            device_class = state.attributes.get("device_class")
            unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, "")

            # If it's an energy sensor, calculate rate
            if device_class == SensorDeviceClass.ENERGY or unit.lower() in [
                "kwh",
                "mwh",
            ]:
                last_val = self._last_energy_values.get(v)
                self._last_energy_values[v] = val
                if last_val is not None and dt_hours > 0:
                    delta = val - last_val
                    if delta < 0:  # Handle reset
                        return 0.0
                    return delta / dt_hours
                return 0.0

            # If it's power, just convert to kW
            if unit.lower() == "w":
                return val / 1000.0
            return val
        except ValueError:
            return 0.0

    def _get_price(self, type_key, value_key):
        """Get price value."""
        t = self.entry.data.get(type_key)
        v = self.entry.data.get(value_key)
        if t == SOURCE_TYPE_FIXED:
            try:
                return float(v)
            except (ValueError, TypeError):
                return 0.0
        state = self.hass.states.get(v)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except ValueError:
                return 0.0
        return 0.0

    def _get_energy_kwh(self, type_key, value_key):
        """Get energy in kWh."""
        t = self.entry.data.get(type_key)
        v = self.entry.data.get(value_key)
        if t == SOURCE_TYPE_FIXED:
            try:
                return float(v)
            except (ValueError, TypeError):
                return 0.0
        state = self.hass.states.get(v)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except ValueError:
                return 0.0
        return 0.0

    def _update_values_and_calculate(self):
        """Update internal values and perform calculation."""
        now = datetime.now()
        if self._last_update is None:
            self._last_update = now
            return

        dt = (now - self._last_update).total_seconds() / 3600.0  # hours
        # We allow small dt for energy calculation, but it needs to be > 0
        if dt < 0.0001:  # less than ~0.3 seconds
            return

        # 1. Fetch current values (kW and Price)
        grid_kw = self._get_kw_value(
            CONF_GRID_IMPORT_SOURCE_TYPE, CONF_GRID_IMPORT_SOURCE_VALUE, dt
        )
        grid_price = self._get_price(
            CONF_GRID_IMPORT_PRICE_TYPE, CONF_GRID_IMPORT_PRICE_VALUE
        )
        solar_kw = self._get_kw_value(
            CONF_SOLAR_SOURCE_TYPE, CONF_SOLAR_SOURCE_VALUE, dt
        )
        solar_price = self._get_price(CONF_SOLAR_PRICE_TYPE, CONF_SOLAR_PRICE_VALUE)
        bat_pow_kw = self._get_kw_value(
            CONF_BATTERY_POWER_SOURCE_TYPE, CONF_BATTERY_POWER_SOURCE_VALUE, dt
        )
        bat_energy_kwh = self._get_energy_kwh(
            CONF_BATTERY_ENERGY_SOURCE_TYPE, CONF_BATTERY_ENERGY_SOURCE_VALUE
        )

        # 2. Update Battery Cost Accumulator
        # Charging (bat_pow_kw < 0)
        if bat_pow_kw < 0:
            charge_kw = abs(bat_pow_kw)
            # Source mix price
            total_source = grid_kw + solar_kw
            if total_source > 0.001:
                mix_price = (
                    grid_kw * grid_price + solar_kw * solar_price
                ) / total_source
                self._total_battery_cost += (charge_kw * dt) * mix_price

        # 3. Determine current Battery Price
        current_battery_price = 0.0
        if bat_energy_kwh > 0.01:
            current_battery_price = self._total_battery_cost / bat_energy_kwh

        # 4. Discharge (bat_pow_kw > 0)
        if bat_pow_kw > 0:
            discharge_kw = bat_pow_kw
            energy_removed = discharge_kw * dt
            # Remove cost from battery proportionally
            self._total_battery_cost -= energy_removed * current_battery_price
            if self._total_battery_cost < 0:
                self._total_battery_cost = 0.0

        # 5. Final Calculation: Cost of supply to the home
        # Home supply = Grid_Import + Solar + Battery_Discharge
        bat_discharge_kw = max(0, bat_pow_kw)
        total_supply_kw = grid_kw + solar_kw + bat_discharge_kw

        if total_supply_kw > 0.001:
            weighted_cost = (
                grid_kw * grid_price
                + solar_kw * solar_price
                + bat_discharge_kw * current_battery_price
            ) / total_supply_kw
            self._state = round(weighted_cost, 4)
        else:
            # If no supply, default to grid price if available
            if grid_price > 0:
                self._state = round(grid_price, 4)

        # Update attributes for transparency
        self._attr_extra_state_attributes = {
            "total_battery_cost": round(self._total_battery_cost, 2),
            "battery_energy_kwh": bat_energy_kwh,
            "battery_unit_price": round(current_battery_price, 4),
            "grid_kw": round(grid_kw, 3),
            "solar_kw": round(solar_kw, 3),
            "battery_kw": round(bat_pow_kw, 3),
            "last_update": now.isoformat(),
        }

        self._last_update = now
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state
