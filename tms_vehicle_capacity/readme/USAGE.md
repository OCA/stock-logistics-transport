# Usage - TMS Vehicle Capacity

## Creating Vehicle Types

### Step 1: Create a Vehicle Type

1. Navigate to **Fleet > Configuration > Vehicle Types**
2. Click **Create** to create a new vehicle type
3. Fill in the required fields:
   - **Type Name**: Name of the vehicle type (e.g., "Van", "VUC", "Toco", "Truck")
   - **Code**: Unique code for the vehicle type (e.g., "VAN", "VUC", "TOCO")
   - **Description**: Optional description of the vehicle type

### Step 2: Configure Default Capacities

For each vehicle type, set default values that will be used when creating vehicles:

- **Default Weight Capacity**: Default weight capacity in kilograms (kg)
- **Default Volume Capacity**: Default volume capacity in cubic meters (m³)
- **Default Cost per KM**: Default cost per kilometer
- **Default Minimum Trip Cost**: Default minimum cost per trip
- **Currency**: Currency for cost fields

**Note**: These are defaults that can be overridden per vehicle.

## Configuring Vehicles

### Step 1: Create or Edit a Vehicle

1. Navigate to **Fleet > Vehicles**
2. Create a new vehicle or edit an existing one

### Step 2: Assign Vehicle Type

1. In the vehicle form, select a **Vehicle Type**
2. When you select a vehicle type, the capacity and cost fields are automatically
   populated with the type's defaults
3. You can override these values per vehicle if needed

### Step 3: Configure Vehicle-Specific Capacities

1. **Weight Capacity**: Set the maximum weight the vehicle can carry (in kg or other
   UoM)
2. **Weight Capacity UoM**: Select the unit of measure (default: kg)
3. **Volume Capacity**: Set the maximum volume the vehicle can carry (in m³ or other
   UoM)
4. **Volume Capacity UoM**: Select the unit of measure (default: m³)

### Step 4: Configure Vehicle Costs

1. **Cost per KM**: Cost per kilometer traveled
2. **Minimum Trip Cost**: Minimum cost for any trip (even if very short)
3. These costs are used by route optimization algorithms

### Step 5: Configure Depot Location (Optional)

1. **Depot Location**: Select the default starting point/depot for this vehicle
2. This is used by route optimization to calculate routes from the depot

### Step 6: Link to TMS Team

1. In the **TMS** tab, select the **TMS Team** this vehicle belongs to
2. Ensure the vehicle type is in the team's allowed vehicle types

## Configuring TMS Teams

### Step 1: Edit TMS Team

1. Navigate to **TMS > Configuration > Teams**
2. Open a team for editing

### Step 2: Configure Allowed Vehicle Types

1. In the **Allowed Vehicle Types** field, select which vehicle types are allowed for
   this team
2. Only vehicles with these types can be used in route optimization for this team

### Step 3: Configure Default Depot

1. Set the **Default Depot Location** for the team
2. This depot must have geolocation coordinates (latitude/longitude)
3. The depot is used as the starting and ending point for optimized routes

## Best Practices

1. **Vehicle Types**: Create vehicle types that match your fleet (Van, VUC, Toco, etc.)
2. **Realistic Capacities**: Set capacities based on actual vehicle specifications
3. **Cost Accuracy**: Use real cost data (fuel, maintenance, driver costs) for accurate
   optimization
4. **Depot Location**: Ensure depot locations have accurate geolocation
5. **Team Configuration**: Configure teams with appropriate vehicle types for your
   operations
