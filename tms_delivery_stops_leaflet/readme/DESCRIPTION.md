This module adds interactive Leaflet map visualization for TMS delivery stops.

## Features

- **Map View for Stops**: View all delivery stops on an interactive Leaflet map
- **Status-based Markers**: Colored markers based on stop status (Draft, Scheduled, Delivered, Skipped)
- **Numbered Markers**: Stops are numbered according to their sequence
- **Route Lines**: Dashed lines connecting stops in sequence order
- **Group by Order**: Stops grouped by their parent order with different colored routes
- **Rich Popups**: Detailed popups showing:
  - Stop sequence and status
  - Partner name and phone
  - Address with navigation link
  - Package count, weight, and volume
  - Scheduled date/time
- **Navigation Button**: Direct link to Google Maps directions
- **Quick Actions**:
  - "Stops Map" button on TMS Order form
  - "View on Map" button on Stop form
  - "View Stops on Map" action for multiple orders
- **Menu Entry**: "Stops Map" menu in TMS for viewing all stops
