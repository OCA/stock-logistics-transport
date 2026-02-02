# Usage - TMS Route Optimizer - Delivery Integration

## Quick Start

1. **Configure Internal Carriers** with auto-create enabled
2. **Create Sales Orders** with delivery addresses
3. **Confirm Sales Orders** to generate pickings
4. **TMS Stops Auto-Created** when pickings are confirmed
5. **Plan Routes** using TMS Route Optimizer
6. **Create TMS Orders** from optimized routes

## Usage Scenarios

### Scenario 1: Automatic Integration (Most Common)

This is the recommended workflow for automatic TMS stop creation from sales orders.

#### Step 1: Setup (One-time)

1. Go to **Inventory > Configuration > Delivery > Delivery Methods**
2. Create or edit an internal carrier:
   - Name: "Company Fleet"
   - Check **Internal Carrier**
   - Select **TMS Team**
   - Check **Auto Create TMS Stops**

#### Step 2: Normal Sales Flow

1. Create a **Sales Order**
2. Set **Delivery Method** to your internal carrier
3. Add products with delivery address
4. **Confirm** the sales order
5. When the **Delivery Order** (picking) is created and confirmed:
   - TMS Stop is **automatically created**
   - Linked to the picking
   - Ready for route optimization

#### Step 3: Plan Routes

1. Go to **TMS > Route Optimizer**
2. Create optimization for the date range
3. Review and optimize routes
4. Create TMS orders from results

### Scenario 2: Manual Stop Creation from Picking

For cases where automatic creation is disabled or you need more control.

#### From Picking Form

1. Open a **Stock Picking** (delivery order)
2. Ensure carrier is set and is **Internal Carrier**
3. Click **Create TMS Stop** button
4. System creates and links TMS stop
5. Proceed with route planning

#### From Multiple Pickings

1. Select multiple pickings in list view
2. Use **Create TMS Stop** action
3. Stops created for all selected pickings

### Scenario 3: Create TMS Orders from Pickings

Use the wizard to quickly create TMS orders from one or more pickings.

#### Single Picking Workflow

1. Open a **Stock Picking** with a TMS stop
2. Click **Create TMS Order** button
3. Select mode:
   - **Create New TMS Order**: Start fresh order
   - **Create Manual Plan**: Draft stops for manual planning
   - **Assign to Existing Order**: Add to existing order

#### Wizard Fields

**Mode: Create New TMS Order**

- **TMS Team**: Required - select team
- **Vehicle**: Optional - assign vehicle
- **Driver**: Optional - assign driver
- **Origin Location**: Optional - start location
- **Destination Location**: Optional - end location
- **Scheduled Start**: Optional - start date/time
- **Description**: Optional - order notes

**Mode: Create Manual Plan**

- Same as above, but stops remain in Draft state
- Allows manual stop reordering and planning
- Good for experienced dispatchers

**Mode: Assign to Existing Order**

- **Existing TMS Order**: Select order to add stops to
- Useful for adding deliveries to partially-filled routes

### Scenario 4: View and Track TMS Information

#### From Stock Picking

1. Open any **Stock Picking**
2. View **TMS Stop** field (if linked)
3. View **TMS Order** field (if stop is in an order)
4. Click **Open TMS Stop** button to see stop details
5. Check **Smart Buttons** for TMS-related information

#### From TMS Stop

1. Go to **TMS > Delivery Stops**
2. Open a stop created from picking
3. View **Picking** field showing source picking
4. View **Sales Order** field (if from sales)
5. View **Picking Reference** for tracking

## Field Mapping

When a TMS stop is created from a picking, the following data is transferred:

| Picking Field     | TMS Stop Field   | Notes                               |
| ----------------- | ---------------- | ----------------------------------- |
| Partner           | Partner          | Delivery address                    |
| Weight            | Weight           | Total weight from stock moves       |
| Volume            | Volume           | From stock_picking_volume           |
| Scheduled Date    | Scheduled Date   | Expected delivery date              |
| Company           | Company          | Company context                     |
| Picking (self)    | Picking ID       | Link back to picking                |

## State Synchronization

The module automatically synchronizes states:

### Picking → TMS Stop State Changes

- **Picking Confirmed** → No change (stop stays Draft)
- **Picking Done** → Stop becomes Scheduled (ready for delivery)
- **Picking Cancelled** → Stop becomes Skipped (not delivered)

### Manual State Changes

- TMS Stop states can be changed manually
- Changes don't affect picking state
- Allows flexibility in route planning

## Integration with Route Optimizer

### Before Optimization

1. **Create Pickings** for all deliveries
2. **Confirm Pickings** to generate TMS stops
3. **Geolocate Partners** if not already done
4. Stops are now in Draft state, ready for optimization

### Run Optimization

1. Go to **TMS > Route Optimizer**
2. Select **Team** (matching carrier's team)
3. Set **Date Range** covering your deliveries
4. System finds all Draft stops in date range
5. **Run Optimization** to plan routes

### After Optimization

1. Review optimized routes
2. **Create Orders** from optimization results
3. Stops are linked to orders and marked Scheduled
4. Original pickings show TMS Order link

## Best Practices

### 1. Partner Data Quality

- Ensure delivery addresses are complete
- Geolocate all partners before confirming orders
- Use **Geo Localize** button on partner form

### 2. Product Configuration

- Set accurate product weights
- Configure product volumes if using volume constraints
- Keep data updated for accurate capacity planning

### 3. Carrier Configuration

- Use different carriers for different service levels
- Link carriers to appropriate TMS teams
- Enable auto-create for standard operations
- Disable auto-create for special handling cases

### 4. Workflow Planning

- Group sales orders by delivery date
- Confirm pickings in batches for same day
- Run route optimization before assigning drivers
- Review routes before creating orders

### 5. Exception Handling

- Pickings without geolocation create stops with warnings
- Review and geolocate before optimization
- Use manual planning mode for special cases

## Troubleshooting

### "No TMS Stop created automatically"

**Check:**

- Is carrier marked as **Internal Carrier**?
- Is **Auto Create TMS Stops** enabled on carrier?
- Is picking type "Outgoing" (delivery)?
- Has picking been confirmed (not just draft)?

**Solution:**

- Update carrier configuration, or
- Use manual **Create TMS Stop** button

### "Cannot create TMS order from picking"

**Check:**

- Does picking have a linked TMS stop?
- If not, click **Create TMS Stop** first

**Solution:**

- Create TMS stop, then use wizard

### "Partner has no geolocation warning"

**Issue:**

- TMS stop created, but partner lacks coordinates
- Cannot be used in route optimization

**Solution:**

- Open partner record
- Click **Geo Localize** action, or
- Manually set Latitude and Longitude

### "Stop already in an order"

**Issue:**

- Trying to create order for stop already assigned

**Check:**

- View TMS Order field on picking
- Stop may already be planned

**Solution:**

- Review existing order, or
- Remove stop from old order first

### "Multiple carriers on picked products"

**Behavior:**

- Only picking-level carrier is considered
- Product-level carriers are ignored

**Solution:**

- Ensure carrier is set at picking level
- Use correct carrier when confirming sales order
