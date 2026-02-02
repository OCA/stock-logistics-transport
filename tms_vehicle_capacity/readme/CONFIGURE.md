# Configuration - TMS Vehicle Capacity

## Module Dependencies

This module requires the following Odoo modules:

- `tms`: Base Transport Management System module
- `fleet`: Fleet management module
- `uom`: Units of Measure support

## Initial Setup

### 1. Create Vehicle Types

Before configuring vehicles, create vehicle types that match your fleet:

1. Go to **Fleet > Configuration > Vehicle Types**
2. Create vehicle types for your fleet (examples):
   - **Van**: Small delivery vehicle
   - **VUC**: Light commercial vehicle
   - **Toco**: Medium truck
   - **Truck**: Large truck
   - **Bitrem**: Articulated truck
3. For each type, configure:
   - Unique code
   - Default weight capacity (kg)
   - Default volume capacity (m³)
   - Default cost per kilometer
   - Default minimum trip cost

**Note**: The module includes demo data with common Brazilian vehicle types.

### 2. Configure Units of Measure (Optional)

If you want to use different units:

1. Go to **TMS > Configuration > Settings > Units**
2. Activate **"Units of measure"**
3. Configure default UoM for weight and volume

### 3. Configure Vehicles

For each vehicle in your fleet:

1. Assign a **Vehicle Type** (auto-populates defaults)
2. Set **Weight Capacity** and **Volume Capacity** (override defaults if needed)
3. Set **Cost per KM** and **Minimum Trip Cost**
4. Optionally set **Depot Location**
5. Link to a **TMS Team**

### 4. Configure TMS Teams

For route optimization:

1. Go to **TMS > Configuration > Teams**
2. For each team:
   - Select **Allowed Vehicle Types** (which types can be used)
   - Set **Default Depot Location** (must have geolocation)

## Integration with Route Optimizer

When used with `tms_route_optimizer`:

1. **Vehicle Types**: Must be configured in team's allowed types
2. **Capacities**: Used to ensure deliveries fit in vehicles
3. **Costs**: Used to calculate optimal route costs
4. **Depot**: Used as starting/ending point for routes

## Data Structure

### Vehicle Type Fields

- `name`: Type name (Van, VUC, etc.)
- `code`: Unique code
- `default_weight_capacity`: Default weight (kg)
- `default_volume_capacity`: Default volume (m³)
- `default_cost_per_km`: Default cost per km
- `default_minimum_trip_cost`: Default minimum cost
- `currency_id`: Currency for costs

### Vehicle Fields (Extended)

- `vehicle_type_id`: Link to vehicle type
- `weight_capacity`: Weight capacity (with UoM)
- `volume_capacity`: Volume capacity (with UoM)
- `cost_per_km`: Cost per kilometer
- `minimum_trip_cost`: Minimum trip cost
- `depot_location_id`: Default depot location

### TMS Team Fields (Extended)

- `allowed_vehicle_type_ids`: Allowed vehicle types for this team
- `default_depot_location_id`: Default depot location (must have geolocation)

## Best Practices

1. **Standardize Types**: Use consistent vehicle type codes across the system
2. **Realistic Capacities**: Base capacities on actual vehicle specifications
3. **Cost Accuracy**: Include all costs (fuel, maintenance, driver, etc.)
4. **Depot Geolocation**: Ensure depot locations have accurate coordinates
5. **Team Organization**: Organize teams by region or operation type
