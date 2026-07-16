# TMS Route Optimizer - Delivery Integration

This module bridges the gap between Odoo's standard delivery/stock management and the
TMS (Transport Management System) by automatically creating TMS delivery stops from
stock pickings that use internal carriers.

## Key Features

- **Automatic TMS Stop Creation**: Automatically creates TMS delivery stops when stock
  pickings are confirmed
- **Internal Carrier Detection**: Identifies when pickings use company-owned vehicles
- **Geolocation Integration**: Links pickings with geolocated delivery addresses
- **State Synchronization**: Keeps picking and TMS stop states synchronized
- **Flexible Order Creation**: Create new TMS orders or assign stops to existing orders
- **Manual Planning Support**: Create draft stops for manual route planning
- **Weight & Volume Tracking**: Automatically transfers weight and volume from pickings
  to TMS stops

## Use Cases

- Automatically create delivery stops from sales orders
- Integrate warehouse operations with transportation planning
- Track deliveries using internal fleet vehicles
- Link sales orders with TMS routes
- Prepare pickings for route optimization
- Maintain delivery visibility from order to delivery

## Technical Details

- **Integration Points**: delivery, stock_delivery, tms, tms_delivery_stops
- **Automatic Triggers**: Stock picking confirmation
- **State Mapping**: Picking states sync with TMS stop states
- **Data Transfer**: Weight, volume, partner, scheduled date from picking to stop
