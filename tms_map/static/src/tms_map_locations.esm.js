import {marker, polygon} from "./lib/leaflet-src.esm.js";
import {GEOFENCE_STYLE, pin} from "./tms_map_pin.esm.js";

export function drawTransportLocations(layer, locations) {
    layer.clearLayers();
    for (const location of locations || []) {
        if (
            location.shape === "area" &&
            location.perimeter &&
            location.perimeter.length >= 3
        ) {
            const area = polygon(location.perimeter, GEOFENCE_STYLE).addTo(layer);
            if (location.name) {
                area.bindTooltip(location.name);
            }
            continue;
        }
        if (!(location.latitude || location.longitude)) {
            continue;
        }
        const placed = marker([location.latitude, location.longitude], {
            icon: pin("fa-map-marker"),
            title: location.name || "",
        });
        if (location.name) {
            placed.bindTooltip(location.name);
        }
        placed.addTo(layer);
    }
}
