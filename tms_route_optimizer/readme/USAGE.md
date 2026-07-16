# Usage - TMS Route Optimizer

## Quick Start

1. **Configure TMS Team** with depot location and allowed vehicle types
2. **Configure Vehicles** with capacities and costs
3. **Create TMS Orders** with delivery stops in Draft state
4. **Run Optimization** from TMS > Route Optimizer
5. **Review Results** and create orders from optimized routes

## Detailed Usage

### Step 1: Access Route Optimizer

1. Navigate to **TMS > Route Optimizer** in the main menu
2. Click **Create** to start a new optimization

### Step 2: Configure Optimization Parameters

Fill in the optimization form:

- **Name**: Optimization name (auto-generated with timestamp)
- **Team**: Select the TMS team (must have depot and allowed vehicle types configured)
- **Optimization Date**: Date for the optimization
- **Date From**: Start date/time for searching delivery stops
- **Date To**: End date/time for searching delivery stops

**Note**: Delivery stops are automatically loaded based on the date range (stops in Draft
state).

### Step 3: Review Delivery Stops

1. The **Delivery Stops** section shows stops found automatically
2. You can:
   - Add stops manually by clicking **Add a line**
   - Remove stops that shouldn't be optimized
   - Verify all stops have geolocation (required)

**Important**: All stops must have partner geolocation (latitude/longitude).

### Step 4: Run Optimization

1. Click the **Run Optimization** button
2. The system will:
   - Validate all data (stops, vehicles, geolocations)
   - Calculate distance matrix between all points
   - Solve the VRP problem using OR-Tools
   - Display results

**Processing Time**: Typically a few seconds for 8-10 stops, may take longer for many
stops.

### Step 5: Analyze Results

After optimization, review:

#### Summary Information

- **Total Cost**: Total cost of all routes
- **Total Distance**: Total distance in kilometers
- **Total Vehicles Used**: Number of vehicles in the solution
- **Optimization Time**: Time taken to solve (seconds)

#### Routes Tab

Each route shows:

- **Vehicle**: Assigned vehicle
- **Stop Count**: Number of stops in route
- **Total Distance**: Route distance (km)
- **Total Weight**: Total weight carried (kg)
- **Total Volume**: Total volume carried (m³)
- **Weight Utilization**: Percentage of weight capacity used
- **Volume Utilization**: Percentage of volume capacity used
- **Route Cost**: Total cost for this route

#### Raw Result Tab

Shows the optimization result in JSON format (useful for debugging or integration).

### Step 6: View Route Details

Click on a route to see:

- Vehicle information
- Capacity utilization (with visual indicators)
- Detailed costs
- **Google Maps URL**: Link to view route on Google Maps
- **Waze URL**: Link for navigation in Waze app
- List of stops in optimized order

### Step 7: Create Orders from Optimization

1. After reviewing results, click **Create Orders**
2. The system will:
   - Create one TMS order per route
   - Add stops in optimized order
   - Link vehicles to orders
   - Update stop states to "Scheduled"
3. You'll be redirected to the list of created orders

## Understanding Results

### Route Structure

Each route follows this pattern:

```
Depot → Stop 1 → Stop 2 → ... → Stop N → Depot
```

All routes start and end at the team's depot location.

### Utilization Metrics

- **Weight Utilization**: `(Total Weight / Vehicle Weight Capacity) × 100`
- **Volume Utilization**: `(Total Volume / Vehicle Volume Capacity) × 100`

Higher utilization (closer to 100%) indicates better capacity usage.

### Cost Calculation

For each route:

```
Route Cost = Minimum Trip Cost + (Total Distance × Cost per KM)
```

Total cost is the sum of all route costs.

## Best Practices

1. **Geolocation**: Ensure all partners have accurate coordinates
2. **Date Range**: Select appropriate date ranges to group nearby deliveries
3. **Vehicle Capacity**: Configure realistic capacities with safety margins
4. **Costs**: Use accurate cost data (fuel, maintenance, driver costs)
5. **Review Before Creating**: Always review routes before creating orders
6. **Use Map Links**: Verify routes using Google Maps/Waze links

## Troubleshooting

### "No delivery stops to optimize"

- Check date range (Date From/Date To)
- Verify stops are in Draft state
- Add stops manually if needed

### "Stop has no geolocation coordinates"

- Configure latitude/longitude for the partner
- Use `base_geolocalize` module to geocode addresses

### "No vehicles available for this team"

- Verify vehicles are linked to the team
- Check vehicle types match team's allowed types
- Ensure vehicles have capacities and costs configured

### "No feasible solution found"

- Total capacity may be insufficient
- Add more vehicles or remove some stops
- Check weight/volume totals vs. vehicle capacities

### Optimization is slow

- Increase `tms.route_optimizer.max_time_seconds` parameter
- Consider splitting stops into multiple optimizations
- Reduce number of stops per optimization
