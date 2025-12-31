# Weighted Energy Cost Sensor for Home Assistant

This Home Assistant custom component provides a sensor that calculates a real-time weighted average cost of electricity per kWh, considering three main sources:
1. **Grid** (Import)
2. **Solar** (Generation)
3. **Battery** (Storage)

## Calculation Logic

The sensor maintains an internal "Cost Basis" for the energy stored in the battery. 

- **Charging**: When the battery charges, the cost of the energy entering the battery is calculated based on the current mix of Grid (at grid price) and Solar (at solar price). This cost is added to the battery's total cost accumulator.
- **Discharging**: When the battery discharges, the energy leaves at the current average price (Total Battery Cost / Total Battery Energy).
- **Consumption**: The final sensor value is the weighted average of all currently providing sources (Grid Import + Solar + Battery Discharge).

This approach automatically accounts for battery round-trip inefficiencies by using the actual stored energy (from a sensor) as the denominator for the battery price.

## Features

- **Multi-step Configuration Wizard**: Easy setup with separate pages for each input.
- **Flexible Inputs**: Choose between Energy Dashboard entities, custom sensors, or fixed values for every parameter.
- **State Persistence**: The battery cost basis is saved across Home Assistant restarts.
- **Unit Awareness**: Automatically detects and handles both Watts (W) and Kilowatts (kW).

## Installation

1. Copy the `weighted_energy_cost` folder to your `custom_components` directory.
2. Restart Home Assistant.
3. Go to Settings -> Devices & Services -> Add Integration -> Search for "Weighted Energy Cost Sensor".

## Configuration

The wizard will guide you through:
- Name for the sensor
- Grid Import Power and Price
- Solar Power and Price
- Battery Power (Positive = Discharge, Negative = Charge)
- Battery Stored Energy (kWh)
