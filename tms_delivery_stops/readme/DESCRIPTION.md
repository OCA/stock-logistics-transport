# TMS Delivery Stops

This module extends the TMS (Transport Management System) module to support multiple
delivery stops per TMS order. It enables businesses to manage complex delivery routes
with multiple destinations, each with its own weight, volume, and geolocation
information.

## Key Features

- **Multiple Delivery Stops**: Add multiple delivery stops to a single TMS order
- **Weight and Volume Tracking**: Track weight and volume for each delivery stop with
  support for Units of Measure (UoM)
- **Geolocation Support**: Automatic geolocation from partner addresses for route
  optimization
- **Stop Sequencing**: Order stops in a sequence to define delivery route order
- **Unloading Time**: Configure minimum unloading time per stop for better time
  estimation
- **State Management**: Track stop states (Draft, Scheduled, Delivered, Skipped)
- **Total Calculations**: Automatic calculation of total weight, volume, and stops per
  order

## Use Cases

- Multi-stop delivery routes
- Route optimization preparation
- Delivery planning and scheduling
- Capacity planning based on weight and volume
- Integration with route optimization algorithms
