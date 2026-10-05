import {Component, onMounted, onWillUnmount, useRef, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {
    divIcon,
    featureGroup,
    map as createMap,
    marker,
    polyline,
    tileLayer,
} from "../../lib/leaflet-src.esm.js";
import {heatLayer} from "../../lib/leaflet-heat.esm.js";

const MODE_ICON = {
    air: "fa-plane",
    water: "fa-ship",
    road: "fa-truck",
    rail: "fa-train-subway",
};
const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

function pin(iconClass) {
    return divIcon({
        className: "",
        html: `<i class="fa ${iconClass} o_tms_map_icon"></i>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
}

export class TmsUniversalMap extends Component {
    static template = "tms_map.TmsUniversalMap";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.mapRef = useRef("map");
        this.state = useState({
            message: "",
            clusters: [],
            trips: [],
            vehicles: [],
        });
        this.map = null;
        this.layer = null;
        this.heat = null;
        this.timer = null;
        this.observer = null;
        onMounted(() => this.start());
        onWillUnmount(() => this.stop());
    }

    get mapMode() {
        if (this.props.mapMode) {
            return this.props.mapMode;
        }
        const action = this.props.action;
        const context = (action && action.context) || {};
        return context.map_mode || "tracking";
    }

    get isAction() {
        return Boolean(this.props.action);
    }

    get title() {
        const titles = {
            dispatch: _t("Dispatch map"),
            heatmap: _t("Position heatmap"),
            tracking: _t("Trip map"),
            geocoding: _t("Location map"),
        };
        return titles[this.mapMode] || _t("Map");
    }

    get resModel() {
        return this.props.record && this.props.record.resModel;
    }

    get resId() {
        return this.props.record && this.props.record.resId;
    }

    async start() {
        const element = this.mapRef.el;
        if (!element) {
            return;
        }
        this.map = createMap(element).setView([20, 0], 2);
        tileLayer(TILES, {
            attribution: "&copy; OpenStreetMap",
            maxZoom: 19,
        }).addTo(this.map);
        this.layer = featureGroup().addTo(this.map);
        this.observer = new ResizeObserver(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        });
        this.observer.observe(element);
        await this.refresh();
        if (this.mapMode === "tracking" && this.resId) {
            this.timer = setInterval(() => this.refresh(), 30000);
        }
    }

    stop() {
        if (this.timer) {
            clearInterval(this.timer);
        }
        if (this.observer) {
            this.observer.disconnect();
        }
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }

    async refresh() {
        this.state.message = "";
        try {
            if (this.mapMode === "geocoding") {
                await this.loadGeocoding();
            } else if (this.mapMode === "tracking") {
                await this.loadTracking();
            } else if (this.mapMode === "dispatch") {
                await this.loadDispatch();
            } else if (this.mapMode === "heatmap") {
                await this.loadHeatmap();
            }
        } catch (error) {
            const data = error && error.data;
            this.state.message =
                (data && data.message) || _t("The map could not be loaded.");
        }
        if (this.map) {
            this.map.invalidateSize();
        }
    }

    clearDrawn() {
        if (this.layer) {
            this.layer.clearLayers();
        }
        if (this.heat && this.map) {
            this.map.removeLayer(this.heat);
            this.heat = null;
        }
    }

    fit(points) {
        if (!this.map || !points.length) {
            return;
        }
        if (points.length === 1) {
            this.map.setView(points[0], 12);
            return;
        }
        this.map.fitBounds(points, {padding: [24, 24]});
    }

    async loadGeocoding() {
        this.clearDrawn();
        if (!this.resId) {
            this.state.message = _t("Save the contact to drop a pin.");
            return;
        }
        const [partner] = await this.orm.read(
            "res.partner",
            [this.resId],
            ["display_name", "partner_latitude", "partner_longitude"]
        );
        const latitude = partner.partner_latitude;
        const longitude = partner.partner_longitude;
        if (latitude || longitude) {
            this.placePartnerPin(latitude, longitude, partner.display_name);
            this.fit([[latitude, longitude]]);
            return;
        }
        this.state.message = _t("Click the map to set the location.");
        this.map.once("click", (event) => {
            this.placePartnerPin(event.latlng.lat, event.latlng.lng);
            this.writePartnerPin(event.latlng);
        });
    }

    placePartnerPin(latitude, longitude, name) {
        this.clearDrawn();
        const placed = marker([latitude, longitude], {
            icon: pin("fa-map-marker"),
            draggable: !this.props.readonly,
            title: name || "",
        });
        placed.on("dragend", () => this.writePartnerPin(placed.getLatLng()));
        placed.addTo(this.layer);
    }

    async writePartnerPin(latlng) {
        await this.orm.call("res.partner", "tms_map_set_coordinates", [
            [this.resId],
            latlng.lat,
            latlng.lng,
        ]);
        this.state.message = "";
        this.fit([[latlng.lat, latlng.lng]]);
    }

    async loadTracking() {
        this.clearDrawn();
        if (!this.resId) {
            this.state.message = _t("Save the trip to see the map.");
            return;
        }
        const data = await this.orm.call(
            "tms.order",
            "get_live_tracking_coordinates",
            [[this.resId]]
        );
        const points = [];
        if (data.origin) {
            this.addNamedPin(data.origin, "fa-sign-in");
            points.push([data.origin.latitude, data.origin.longitude]);
        }
        if (data.destination) {
            this.addNamedPin(data.destination, "fa-flag");
            points.push([data.destination.latitude, data.destination.longitude]);
        }
        if (data.path && data.path.length) {
            polyline(data.path, {color: "#1f4e79", weight: 4}).addTo(this.layer);
        }
        const vehicle = data.vehicle;
        if (vehicle && (vehicle.latitude || vehicle.longitude)) {
            const iconClass = MODE_ICON[vehicle.mode] || MODE_ICON.road;
            marker([vehicle.latitude, vehicle.longitude], {
                icon: pin(iconClass),
                title: vehicle.name || "",
                zIndexOffset: 1000,
            }).addTo(this.layer);
            points.push([vehicle.latitude, vehicle.longitude]);
        }
        this.fit(points);
    }

    addNamedPin(point, iconClass) {
        marker([point.latitude, point.longitude], {
            icon: pin(iconClass),
            title: point.name || "",
        }).addTo(this.layer);
    }

    async loadDispatch() {
        this.clearDrawn();
        const [clusters, trips, vehicles] = await Promise.all([
            this.orm.call("tms.cargo", "tms_map_unassigned_clusters", []),
            this.orm.call("tms.order", "tms_map_open_trips", []),
            this.orm.call("tms.order", "tms_map_vehicle_positions", []),
        ]);
        this.state.clusters = clusters;
        this.state.trips = trips;
        this.state.vehicles = vehicles;
        const points = [];
        for (const vehicle of vehicles) {
            const iconClass = MODE_ICON[vehicle.mode] || MODE_ICON.road;
            const placed = marker([vehicle.latitude, vehicle.longitude], {
                icon: pin(iconClass),
                title: vehicle.name,
                zIndexOffset: 500,
            });
            placed.bindPopup(this.vehiclePopup(vehicle));
            placed.addTo(this.layer);
            points.push([vehicle.latitude, vehicle.longitude]);
        }
        for (const cluster of clusters) {
            if (!(cluster.latitude || cluster.longitude)) {
                continue;
            }
            const placed = marker([cluster.latitude, cluster.longitude], {
                icon: pin("fa-cubes"),
                title: cluster.name,
            });
            placed.bindPopup(this.clusterPopup(cluster));
            placed.addTo(this.layer);
            points.push([cluster.latitude, cluster.longitude]);
        }
        this.fit(points);
        if (!vehicles.length && !clusters.length) {
            this.state.message = _t("No vehicle positions yet.");
        }
    }

    vehiclePopup(vehicle) {
        const root = document.createElement("div");
        root.className = "o_tms_map_popup";
        const title = document.createElement("strong");
        title.textContent = vehicle.name;
        root.appendChild(title);
        if (vehicle.date) {
            const when = document.createElement("div");
            when.textContent = vehicle.date;
            root.appendChild(when);
        }
        return root;
    }

    clusterPopup(cluster) {
        const root = document.createElement("div");
        root.className = "o_tms_map_popup";
        const title = document.createElement("strong");
        title.textContent = cluster.name;
        root.appendChild(title);
        const count = document.createElement("div");
        count.textContent = _t("%s cargo", cluster.cargo.length);
        root.appendChild(count);
        return root;
    }

    async assignCluster(cluster, ev) {
        const select = ev.currentTarget.parentElement.querySelector("select");
        const tripId = Number(select && select.value);
        if (!tripId) {
            this.notification.add(_t("Choose a trip."), {type: "warning"});
            return;
        }
        const ids = cluster.cargo.map((line) => line.id);
        try {
            await this.orm.call("tms.cargo", "tms_map_assign", [ids, tripId]);
            await this.loadDispatch();
        } catch (error) {
            const data = error && error.data;
            this.notification.add(
                (data && data.message) || _t("Cargo could not be assigned."),
                {type: "danger"}
            );
        }
    }

    async loadHeatmap() {
        this.clearDrawn();
        const points = await this.orm.call("tms.order", "tms_map_heatmap", []);
        if (!points.length) {
            this.state.message = _t("No odometer positions yet.");
            return;
        }
        this.heat = heatLayer(points, {radius: 25, blur: 15, maxZoom: 12});
        this.heat.addTo(this.map);
        this.fit(points.map((point) => [point[0], point[1]]));
    }
}

registry.category("actions").add("tms_map", TmsUniversalMap);
registry.category("view_widgets").add("tms_map", {
    component: TmsUniversalMap,
    extractProps: ({attrs}) => ({
        mapMode: attrs.mode,
    }),
});
