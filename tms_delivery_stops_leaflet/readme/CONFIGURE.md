## Prerequisites

1. **Coordinates**: Partners must have latitude/longitude set
   - Use the base_geolocalize module to geocode addresses
   - Or manually set `partner_latitude` and `partner_longitude` fields

2. **Tile Server**: Configure the Leaflet tile server in system parameters
   - `leaflet.tile_url`: Map tile URL (default: OpenStreetMap)
   - `leaflet.copyright`: Attribution text

## No Additional Configuration Required

This module works out of the box once:
- Partners have coordinates
- Delivery stops are created with partners
