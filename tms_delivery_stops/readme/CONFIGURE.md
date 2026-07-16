# Configuration - TMS Delivery Stops

## Module Dependencies

This module requires the following Odoo modules:

- `tms`: Base Transport Management System module
- `base_geolocalize`: For geocoding partner addresses
- `uom`: Units of Measure support

## Required Configuration

### 1. Enable Units of Measure (Optional but Recommended)

If you want to use different units for weight and volume:

1. Go to **TMS > Configuration > Settings > Units**
2. Activate the **"Units of measure"** checkbox
3. Save the changes
4. Configure default UoM for weight and volume in the settings

### 2. Configure Partners with Geolocation

For route optimization to work, all delivery partners must have geolocation:

1. Go to **Contacts** and open a partner
2. Ensure the partner has a complete address (street, city, state, country)
3. Use the **Geolocate** button (if `base_geolocalize` is installed) to automatically
   fetch coordinates
4. Alternatively, manually set `partner_latitude` and `partner_longitude` fields

**Note**: Partners without geolocation will not appear in route optimization.

### 3. Configure TMS Teams (For Route Optimization)

If using with `tms_route_optimizer`:

1. Go to **TMS > Configuration > Teams**
2. Configure the team with:
   - **Default Depot Location**: Starting point for routes (must have geolocation)
   - **Allowed Vehicle Types**: Types of vehicles allowed for this team

## Optional Settings

### Default Unloading Time

The default unloading time per stop is 30 minutes. This can be adjusted per stop in the
delivery stop form.

### Stop State Workflow

The module uses the following state workflow:

- **Draft** → **Scheduled** → **Delivered** or **Skipped**

States can be changed manually or automatically by route optimization modules.

## Integration with Route Optimizer

When used with `tms_route_optimizer`:

1. Ensure all stops are in **Draft** state
2. Set appropriate **Scheduled Date** for each stop
3. Fill in **Weight** and **Volume** for capacity planning
4. Ensure all partners have geolocation

The route optimizer will automatically:
- Find stops in Draft state within a date range
- Optimize the route order
- Update stops to Scheduled state when orders are created
