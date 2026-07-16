# Configuration - TMS Route Optimizer

## Module Dependencies

This module requires the following Odoo modules:

- `tms`: Base Transport Management System module
- `tms_delivery_stops`: Multiple delivery stops per order
- `tms_vehicle_capacity`: Vehicle types with capacity and cost management
- `base_geolocalize`: Geolocation support for partners

## External Dependencies

### Python Package: OR-Tools

Install the Google OR-Tools Python package:

```bash
pip install ortools
```

**Note**: This is required for the optimization algorithm to work.

## Required Configuration

### 1. Configure TMS Team

1. Go to **TMS > Configuration > Teams**
2. For each team used in optimization:
   - **Default Depot Location**: Select a partner with geolocation (latitude/longitude)
     - This is the starting and ending point for all routes
   - **Allowed Vehicle Types**: Select vehicle types that can be used in this team
     - Only vehicles with these types will be considered

**Critical**: The depot location MUST have geolocation coordinates configured.

### 2. Configure Vehicles

1. Go to **Fleet > Vehicles**
2. For each vehicle:
   - **Vehicle Type**: Must match one of the team's allowed types
   - **Weight Capacity**: Maximum weight capacity (kg)
   - **Volume Capacity**: Maximum volume capacity (m³)
   - **Cost per KM**: Cost per kilometer traveled
   - **Minimum Trip Cost**: Minimum cost for any trip
   - **TMS Team**: Link to the appropriate team

### 3. Configure Delivery Stops

1. Create TMS orders with delivery stops (using `tms_delivery_stops` module)
2. Ensure all stops:
   - Are in **Draft** state (for optimization)
   - Have partners with **geolocation** (latitude/longitude)
   - Have **weight** and **volume** defined (for capacity planning)
   - Have **scheduled date** set (for date range filtering)

### 4. Configure System Parameters (Optional)

Go to **Settings > Technical > Parameters > System Parameters**:

- **`tms.route_optimizer.max_time_seconds``**: Maximum time for optimization (default:
  300 seconds / 5 minutes)
  - Increase for complex problems with many stops
- **`tms.route_optimizer.max_deliveries`**: Maximum number of deliveries (default: 100)
  - Limits the number of stops that can be optimized at once

## Optimization Workflow

### Prerequisites Checklist

Before running optimization, ensure:

- [ ] OR-Tools Python package is installed
- [ ] TMS team has depot location with geolocation
- [ ] TMS team has allowed vehicle types configured
- [ ] Vehicles are configured with capacities and costs
- [ ] Vehicles are linked to the team
- [ ] Delivery stops exist in Draft state
- [ ] All delivery partners have geolocation
- [ ] Stops have weight and volume defined

### Optimization Process

1. **Select Team**: Choose team with configured depot and vehicles
2. **Set Date Range**: Define period for finding delivery stops
3. **Review Stops**: Verify all stops have required data
4. **Run Optimization**: Execute the VRP solver
5. **Review Results**: Check routes, utilization, and costs
6. **Create Orders**: Generate TMS orders from optimized routes

## Integration Points

### With tms_delivery_stops

- Finds stops in Draft state within date range
- Updates stops to Scheduled state when orders are created
- Uses stop weight/volume for capacity constraints
- Uses stop geolocation for distance calculation

### With tms_vehicle_capacity

- Uses vehicle weight/volume capacity as constraints
- Uses vehicle cost per KM and minimum trip cost
- Filters vehicles by team's allowed vehicle types
- Uses team's default depot location

## Algorithm Configuration

### Distance Calculation

- Uses **Haversine formula** for great-circle distances
- Calculates distances between:
  - Depot and all stops
  - All stops to each other

### Optimization Constraints

- **Capacity**: Total weight/volume cannot exceed vehicle capacity
- **Vehicle Availability**: Only vehicles in the team are considered
- **Vehicle Types**: Only allowed vehicle types are used

### Optimization Objective

Minimizes total cost:

```
Total Cost = Σ (Minimum Trip Cost + Distance × Cost per KM)
```

For all routes in the solution.

## Performance Tuning

### For Many Stops (>50)

1. Increase `max_time_seconds` parameter
2. Consider splitting into multiple optimizations (by region)
3. Filter stops by date range to reduce problem size

### For Better Solutions

1. Ensure accurate geolocation coordinates
2. Use realistic vehicle capacities
3. Configure accurate cost data
4. Allow sufficient optimization time

## Troubleshooting Configuration

### "No vehicles available"

- Check vehicle types match team's allowed types
- Verify vehicles are linked to the team
- Ensure vehicles have capacities configured

### "Depot has no geolocation"

- Configure `partner_latitude` and `partner_longitude` for depot partner
- Use `base_geolocalize` module to geocode address

### "OR-Tools not found"

- Install: `pip install ortools`
- Restart Odoo server after installation

### Optimization timeout

- Increase `tms.route_optimizer.max_time_seconds`
- Reduce number of stops per optimization
- Split into multiple smaller optimizations
