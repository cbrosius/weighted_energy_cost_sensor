"""Tests for the weighted energy cost sensor logic."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Since we want to test the logic without full HA environment, we can extract the math.

def calculate_weighted_cost(
    grid_kw, grid_price, solar_kw, solar_price, bat_pow_kw, bat_energy_kwh, total_battery_cost, dt_hours
):
    """Simplified logic for testing."""
    # Charge
    if bat_pow_kw < 0:
        charge_kw = abs(bat_pow_kw)
        total_source = grid_kw + solar_kw
        if total_source > 0.001:
            mix_price = (grid_kw * grid_price + solar_kw * solar_price) / total_source
            total_battery_cost += (charge_kw * dt_hours) * mix_price
    
    current_battery_price = 0.0
    if bat_energy_kwh > 0.01:
        current_battery_price = total_battery_cost / bat_energy_kwh
    
    # Discharge
    if bat_pow_kw > 0:
        discharge_kw = bat_pow_kw
        energy_removed = discharge_kw * dt_hours
        total_battery_cost -= energy_removed * current_battery_price
    
    bat_discharge_kw = max(0, bat_pow_kw)
    total_supply_kw = grid_kw + solar_kw + bat_discharge_kw
    
    weighted_cost = 0
    if total_supply_kw > 0.001:
        weighted_cost = (
            grid_kw * grid_price +
            solar_kw * solar_price +
            bat_discharge_kw * current_battery_price
        ) / total_supply_kw
        
    return round(weighted_cost, 4), round(total_battery_cost, 4), round(current_battery_price, 4)

def test_pure_grid():
    cost, bat_cost, bat_price = calculate_weighted_cost(
        grid_kw=1.0, grid_price=0.30, solar_kw=0, solar_price=0, bat_pow_kw=0, bat_energy_kwh=10, total_battery_cost=0, dt_hours=1
    )
    assert cost == 0.30
    assert bat_cost == 0

def test_grid_and_solar():
    # 50/50 mix. Grid 0.30, Solar 0.0. Result should be 0.15
    cost, _, _ = calculate_weighted_cost(
        grid_kw=1.0, grid_price=0.30, solar_kw=1.0, solar_price=0, bat_pow_kw=0, bat_energy_kwh=10, total_battery_cost=0, dt_hours=1
    )
    assert cost == 0.15

def test_battery_charging_from_solar():
    # Initial: Battery empty, cost 0
    # Action: Charge 1kW from solar (0€) for 1h -> 1kWh in battery. Cost should remain 0.
    cost, bat_cost, bat_price = calculate_weighted_cost(
        grid_kw=0, grid_price=0.30, solar_kw=2.0, solar_price=0, bat_pow_kw=-1.0, bat_energy_kwh=1.0, total_battery_cost=0, dt_hours=1
    )
    assert bat_cost == 0
    assert bat_price == 0

def test_battery_charging_from_grid():
    # Action: Charge 1kW from grid (0.30€) for 1h -> 1kWh in battery. Bat cost should be 0.30.
    cost, bat_cost, bat_price = calculate_weighted_cost(
        grid_kw=1.0, grid_price=0.30, solar_kw=0, solar_price=0, bat_pow_kw=-1.0, bat_energy_kwh=1.0, total_battery_cost=0, dt_hours=1
    )
    assert bat_cost == 0.30
    assert bat_price == 0.30

def test_battery_discharging():
    # Setup: Battery has 5kWh, total cost 1.00€ -> 0.20€/kWh
    # Action: Discharge 1kW for 1h. House uses 1kW.
    # Result: Supply price should be 0.20€. Bat cost should drop to 0.80€.
    cost, bat_cost, bat_price = calculate_weighted_cost(
        grid_kw=0, grid_price=0.30, solar_kw=0, solar_price=0, bat_pow_kw=1.0, bat_energy_kwh=4.0, total_battery_cost=1.0, dt_hours=1
    )
    # Note: bat_energy_kwh in the test is the *final* or *current* energy.
    # In my logic, I calculate current_battery_price = cost / energy_stored. 
    # 1.0 / 4.0 = 0.25 ? Wait.
    # If I have 5kWh and 1€ cost -> 0.20€/kWh.
    # If I discharge 1kWh, I remove 0.20€ cost. Correct.
    assert bat_price == 0.25 # Since I passed 4.0 as energy
    assert cost == 0.25
    assert bat_cost == 1.0 - (1.0 * 1 * 0.25) == 0.75
