# Configuration - TMS Route Optimizer - Delivery Integration

## Module Dependencies

This module requires the following Odoo modules:

- `delivery`: Standard Odoo delivery management
- `sale_stock`: Link sales orders with stock operations
- `stock_delivery`: Stock picking delivery integration
- `tms`: Base Transport Management System module
- `tms_delivery_stops`: Multiple delivery stops per order
- `base_geolocalize`: Geolocation support for partners
- `stock_picking_volume`: Volume calculation for pickings

## Required Configuration

### 1. Configure Delivery Carriers

1. Go to **Inventory > Configuration > Delivery > Delivery Methods**
2. For each carrier representing your internal fleet:
   - Enable **Internal Carrier** checkbox
     - This marks the carrier as company-owned
   - Select a **TMS Team** (optional)
     - Default team for pickings using this carrier
   - Enable **Auto Create TMS Stops** (optional)
     - Automatically create stops when pickings are confirmed

### 2. Configure Partner Geolocation

For automatic TMS integration to work effectively:

1. Go to **Contacts**
2. For each delivery partner:
   - Ensure the address is complete
   - Use **Geo Localize** action to get coordinates
   - Or manually set **Latitude** and **Longitude**

**Important**: Partners without geolocation can still have TMS stops created, but
will need manual geocoding before route optimization.

### 3. Configure Products (Weight & Volume)

For accurate capacity planning:

1. Go to **Inventory > Products**
2. For each product:
   - Set **Weight** in the Inventory tab
   - Set **Volume** (if using `stock_picking_volume` module)

This data is automatically transferred to TMS stops when pickings are confirmed.

## Integration Workflow

### Automatic Integration (Recommended)

1. **Sales Order**: Create sales order with delivery address
2. **Delivery Method**: Select an internal carrier with auto-create enabled
3. **Confirm Order**: Sales order creates delivery order (picking)
4. **Picking Confirmation**: When picking is confirmed, TMS stop is auto-created
5. **Route Planning**: Use TMS Route Optimizer to plan routes
6. **Order Creation**: Create TMS orders from optimized routes

### Manual Integration

1. **Create Picking**: Create outgoing picking with internal carrier
2. **Confirm Picking**: Confirm the picking to make it ready
3. **Manual Stop Creation**: Click **Create TMS Stop** button on picking
4. **Plan Routes**: Use TMS Route Optimizer or manual planning
5. **Create Orders**: Create TMS orders for deliveries

## Carrier Configuration Examples

### Example 1: Fleet with Automatic Integration

```
Carrier Name: Company Fleet - North
Internal Carrier: ✓ Yes
TMS Team: North Operations
Auto Create TMS Stops: ✓ Yes
```

When a picking uses this carrier and is confirmed, a TMS stop is automatically
created and linked to the North Operations team.

### Example 2: Fleet with Manual Planning

```
Carrier Name: Company Fleet - Express
Internal Carrier: ✓ Yes
TMS Team: Express Delivery
Auto Create TMS Stops: ✗ No
```

Pickings with this carrier need manual TMS stop creation using the button on the
picking form.

## State Synchronization

The module automatically synchronizes states between pickings and TMS stops:

| Picking State | TMS Stop State | Action                              |
| ------------- | -------------- | ----------------------------------- |
| Confirmed     | Draft          | Initial creation                    |
| Assigned      | Draft          | No change (waiting for delivery)    |
| Done          | Scheduled      | Updated when picking is delivered   |
| Cancelled     | Skipped        | Marked as skipped (not delivered)   |

## Integration with TMS Route Optimizer

This module creates TMS stops that can be optimized by `tms_route_optimizer`:

1. **Stops Created**: From pickings with internal carriers
2. **Data Populated**: Weight, volume, partner, geolocation, scheduled date
3. **State**: Created in Draft state (ready for optimization)
4. **Optimization**: Use TMS Route Optimizer to plan routes
5. **Orders**: Create TMS orders from optimized routes

## Wizard Options

The **Create TMS Order** wizard provides three modes:

### Mode 1: Create New TMS Order

- Creates a new TMS order
- Assigns selected stops to the new order
- Marks stops as "Scheduled"
- Requires: Team, Vehicle (optional), Driver (optional)

### Mode 2: Create Manual Plan

- Creates a new TMS order with stops in Draft state
- Allows manual route planning and reordering
- Useful when route optimization is not needed

### Mode 3: Assign to Existing Order

- Adds stops to an existing TMS order
- Useful for adding deliveries to partially-filled routes
- Maintains existing route structure

## Troubleshooting Configuration

### "No TMS Stop button appears"

- Ensure carrier is marked as **Internal Carrier**
- Check picking type is "Outgoing" (delivery order)
- Verify it's not a return picking

### "TMS Stop not automatically created"

- Check **Auto Create TMS Stops** is enabled on carrier
- Ensure picking is confirmed (not just draft)
- Verify carrier is set on picking

### "Partner has no geolocation warning"

- This is informational only - stop is still created
- Geolocate the partner to enable route optimization
- Go to partner form and use **Geo Localize** action

### "Cannot create TMS Stop"

- Verify picking is outgoing type
- Check carrier is marked as internal
- Ensure TMS modules are properly installed
