# Usage - TMS Delivery Stops

## Creating TMS Orders with Multiple Delivery Stops

### Step 1: Create a TMS Order

1. Navigate to **TMS > Orders**
2. Click **Create** to create a new order
3. Fill in the basic order information (driver, vehicle, etc.)

### Step 2: Add Delivery Stops

1. In the TMS Order form, scroll to the **Delivery Stops** section
2. Click **Add a line** to add a new delivery stop
3. For each stop, fill in:
   - **Delivery Partner**: Select the customer/recipient (must have geolocation)
   - **Sequence**: Order of the stop in the route (use handle to drag and reorder)
   - **Weight**: Weight of the delivery (optional)
   - **Weight UoM**: Unit of measure for weight (kg, lb, etc.)
   - **Volume**: Volume of the delivery (optional)
   - **Volume UoM**: Unit of measure for volume (m³, ft³, etc.)
   - **Unloading Time**: Minimum unloading time in minutes (default: 30)
   - **Scheduled Date**: Planned delivery date and time
   - **State**: Current state of the stop (Draft, Scheduled, Delivered, Skipped)

### Step 3: Configure Geolocation

For route optimization to work, all delivery partners must have geolocation:

1. Ensure the partner has a complete address
2. The system will automatically fetch latitude/longitude from the partner
3. If geolocation is missing, use the `base_geolocalize` module to geocode addresses

### Step 4: View Stop Information

- **Total Weight**: Automatically calculated sum of all stop weights
- **Total Volume**: Automatically calculated sum of all stop volumes
- **Total Stops**: Count of delivery stops
- **Estimated Total Time**: Sum of all unloading times converted to hours

## Managing Stop States

- **Draft**: Initial state when stop is created
- **Scheduled**: Stop has been scheduled for delivery (used by route optimizer)
- **Delivered**: Stop has been completed
- **Skipped**: Stop was skipped (e.g., customer not available)

## Best Practices

1. **Geolocation**: Always ensure partners have accurate geolocation for route
   optimization
2. **Sequence**: Use the sequence field or drag handles to order stops logically
3. **Weight/Volume**: Fill in accurate weight and volume for capacity planning
4. **Unloading Time**: Set realistic unloading times based on cargo type
5. **Scheduled Dates**: Set appropriate scheduled dates for better route optimization
