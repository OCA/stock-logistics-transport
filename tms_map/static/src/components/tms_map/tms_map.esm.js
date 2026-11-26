import {
    Component,
    onMounted,
    onWillUnmount,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {
    featureGroup,
    map as createMap,
    marker,
    polygon,
    polyline,
    tileLayer,
} from "../../lib/leaflet-src.esm.js";
import {heatLayer} from "../../lib/leaflet-heat.esm.js";
import {
    GEOFENCE_STYLE,
    modeIcon,
    motionLabel,
    motionLegend as motionLegendItems,
    parsePerimeter,
    pin,
    vehiclePinClass as vehiclePinClassName,
} from "../../tms_map_pin.esm.js";
import {drawTransportLocations} from "../../tms_map_locations.esm.js";

const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const HISTORY_COLORS = ["#1f4e79", "#2e7d32", "#ef6c00", "#6a1b9a", "#00838f"];
const MOTION_RANK = {off: 0, idle: 1, moving: 2};

function byStatus(left, right) {
    const rank = (row) =>
        Object.prototype.hasOwnProperty.call(MOTION_RANK, row.motion)
            ? MOTION_RANK[row.motion]
            : 3;
    const delta = rank(left) - rank(right);
    if (delta) {
        return delta;
    }
    return (left.name || "").localeCompare(right.name || "");
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
            history: [],
            selectedTripIds: [],
            selectSeveral: false,
            selectedVehicleId: false,
            syncList: true,
            bounds: null,
            drawing: false,
            cornerCount: 0,
        });
        this.draft = [];
        this.onMapClick = (event) => {
            if (this.state.drawing) {
                this.addCorner(event.latlng);
            }
        };
        this.map = null;
        this.layer = null;
        this.heat = null;
        this.markers = {};
        this.timer = null;
        this.observer = null;
        onMounted(() => this.start());
        onWillUnmount(() => this.stop());
        useEffect(
            () => {
                if (this.map && this.mapMode === "geocoding" && this.resId) {
                    this.loadGeocoding();
                }
            },
            () => {
                const data = (this.props.record && this.props.record.data) || {};
                return [data.tms_map_shape, JSON.stringify(data.tms_geofence || "")];
            }
        );
        this.searchReady = false;
        useEffect(
            () => {
                if (!this.searchReady) {
                    this.searchReady = true;
                    return;
                }
                if (this.map && this.props.searchModelName) {
                    this.refresh();
                }
            },
            () => [JSON.stringify(this.props.searchDomain || [])]
        );
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

    get actionContext() {
        const action = this.props.action;
        return (action && action.context) || {};
    }

    get fleetTeamId() {
        const context = this.actionContext;
        if (context.active_model === "tms.team" && context.active_id) {
            return context.active_id;
        }
        return context.tms_team_id || false;
    }

    get historyVehicleId() {
        const context = this.actionContext;
        if (context.vehicle_id) {
            return context.vehicle_id;
        }
        if (context.active_model === "fleet.vehicle" && context.active_id) {
            return context.active_id;
        }
        return false;
    }

    get showMotionLegend() {
        return (
            this.mapMode === "dispatch" ||
            this.mapMode === "tracking" ||
            this.mapMode === "fleet"
        );
    }

    get fleetRows() {
        let rows = this.state.vehicles.slice();
        const bounds = this.state.bounds;
        if (this.state.syncList && bounds) {
            rows = rows.filter((vehicle) => {
                if (!(vehicle.latitude || vehicle.longitude)) {
                    return false;
                }
                return (
                    vehicle.latitude >= bounds.south &&
                    vehicle.latitude <= bounds.north &&
                    vehicle.longitude >= bounds.west &&
                    vehicle.longitude <= bounds.east
                );
            });
        }
        rows.sort(byStatus);
        return rows;
    }

    get motionLegend() {
        return motionLegendItems();
    }

    vehiclePinClass(vehicle) {
        return vehiclePinClassName(vehicle);
    }

    motionLabel(motion) {
        return motionLabel(motion);
    }

    get syncLabel() {
        return _t("Update the list with the map");
    }

    get sortLabel() {
        return _t("Sort by status");
    }

    get severalLabel() {
        return _t("Select several");
    }

    get noDriverLabel() {
        return _t("No driver");
    }

    get isArea() {
        const data = (this.props.record && this.props.record.data) || {};
        return data.tms_map_shape === "area";
    }

    get showDrawTools() {
        return this.mapMode === "geocoding" && this.isArea && !this.props.readonly;
    }

    get closePerimeterLabel() {
        return _t("Close perimeter");
    }

    get clearPerimeterLabel() {
        return _t("Clear");
    }

    get title() {
        const titles = {
            dispatch: _t("Dispatch map"),
            heatmap: _t("Position heatmap"),
            tracking: _t("Trip map"),
            geocoding: _t("Location map"),
            fleet: _t("Live fleet"),
            history: _t("Trip history"),
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
        this.locations = featureGroup().addTo(this.map);
        this.layer = featureGroup().addTo(this.map);
        this.map.on("moveend", () => this.rememberBounds());
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
            } else if (this.mapMode === "fleet") {
                await this.loadFleet();
            } else if (this.mapMode === "history") {
                await this.loadHistory();
            }
        } catch (error) {
            const data = error && error.data;
            this.state.message =
                (data && data.message) || _t("The map could not be loaded.");
        }
        await this.overlayLocations();
        if (this.map) {
            this.map.invalidateSize();
        }
    }

    async restrict(rows, model) {
        if (this.props.searchModelName !== model) {
            return rows;
        }
        const ids = await this.orm.search(model, this.props.searchDomain || []);
        const allowed = new Set(ids);
        return rows.filter((row) => allowed.has(row.id));
    }

    async overlayLocations() {
        if (!this.locations) {
            return;
        }
        const rows = await this.orm.call("res.partner", "tms_map_locations", []);
        const skip = this.mapMode === "geocoding" ? this.resId : false;
        drawTransportLocations(
            this.locations,
            skip ? rows.filter((row) => row.id !== skip) : rows
        );
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
        this.draft = [];
        this.state.drawing = false;
        this.state.cornerCount = 0;
        if (this.map) {
            this.map.off("click", this.onMapClick);
        }
        if (!this.resId) {
            this.state.message = _t("Save the contact to drop a pin.");
            return;
        }
        const [partner] = await this.orm.read("res.partner", [this.resId], [
            "display_name",
            "partner_latitude",
            "partner_longitude",
            "tms_map_shape",
            "tms_geofence",
        ]);
        const data = (this.props.record && this.props.record.data) || {};
        const shape = data.tms_map_shape || partner.tms_map_shape;
        if (shape === "area") {
            const corners = parsePerimeter(
                data.tms_geofence || partner.tms_geofence
            );
            if (corners.length >= 3) {
                this.drawPerimeter(corners, partner.display_name);
                return;
            }
            this.startDrawing();
            return;
        }
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

    startDrawing() {
        this.state.drawing = true;
        this.state.message = _t("Click the map to mark the corners of the perimeter.");
        this.map.off("click", this.onMapClick);
        this.map.on("click", this.onMapClick);
    }

    addCorner(latlng) {
        this.draft.push([latlng.lat, latlng.lng]);
        this.state.cornerCount = this.draft.length;
        this.redrawDraft();
    }

    redrawDraft() {
        this.clearDrawn();
        if (this.draft.length >= 2) {
            polyline(this.draft, {color: "#1f4e79", weight: 3}).addTo(this.layer);
        }
        for (const corner of this.draft) {
            marker(corner, {icon: pin("fa-circle")}).addTo(this.layer);
        }
        this.fit(this.draft);
    }

    async closePerimeter() {
        if (this.draft.length < 3) {
            this.notification.add(_t("A perimeter needs at least three corners."), {
                type: "warning",
            });
            return;
        }
        await this.orm.call("res.partner", "tms_map_set_geofence", [
            [this.resId],
            this.draft,
        ]);
        this.state.drawing = false;
        this.state.message = "";
        if (this.map) {
            this.map.off("click", this.onMapClick);
        }
        this.drawPerimeter(this.draft);
    }

    async clearPerimeter() {
        this.draft = [];
        this.state.cornerCount = 0;
        if (this.resId) {
            await this.orm.call("res.partner", "tms_map_set_geofence", [
                [this.resId],
                [],
            ]);
        }
        this.clearDrawn();
        this.startDrawing();
    }

    drawPerimeter(corners, name) {
        this.clearDrawn();
        this.draft = corners.map((corner) => [corner[0], corner[1]]);
        this.state.cornerCount = this.draft.length;
        this.state.drawing = false;
        const area = polygon(this.draft, GEOFENCE_STYLE).addTo(this.layer);
        if (name) {
            area.bindTooltip(name);
        }
        this.draft.forEach((corner, index) => {
            const handle = marker(corner, {
                icon: pin("fa-circle"),
                draggable: !this.props.readonly,
            });
            handle.on("drag", () => {
                const latlng = handle.getLatLng();
                this.draft[index] = [latlng.lat, latlng.lng];
                area.setLatLngs(this.draft);
            });
            handle.on("dragend", () => this.writePerimeter());
            handle.addTo(this.layer);
        });
        this.fit(this.draft);
    }

    async writePerimeter() {
        await this.orm.call("res.partner", "tms_map_set_geofence", [
            [this.resId],
            this.draft,
        ]);
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
            marker([vehicle.latitude, vehicle.longitude], {
                icon: pin(modeIcon(vehicle.mode), vehicle.motion || "off"),
                title: this.pinTitle(vehicle.name, vehicle.motion),
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
        const [clusters, trips, positions] = await Promise.all([
            this.orm.call("tms.cargo", "tms_map_unassigned_clusters", []),
            this.orm.call("tms.order", "tms_map_open_trips", []),
            this.orm.call("tms.order", "tms_map_vehicle_positions", []),
        ]);
        const vehicles = await this.restrict(positions, "fleet.vehicle");
        this.state.clusters = clusters;
        this.state.trips = trips;
        this.state.vehicles = vehicles;
        const points = [];
        for (const vehicle of vehicles) {
            const placed = marker([vehicle.latitude, vehicle.longitude], {
                icon: pin(modeIcon(vehicle.mode), vehicle.motion || "off"),
                title: this.pinTitle(vehicle.name, vehicle.motion),
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
        if (vehicle.driver) {
            const driver = document.createElement("div");
            driver.textContent = vehicle.driver;
            root.appendChild(driver);
        }
        const status = motionLabel(vehicle.motion);
        if (status) {
            const line = document.createElement("div");
            line.textContent = status;
            root.appendChild(line);
        }
        if (vehicle.date) {
            const when = document.createElement("div");
            when.textContent = vehicle.date;
            root.appendChild(when);
        }
        return root;
    }

    pinTitle(name, motion) {
        const status = motionLabel(motion);
        return status ? `${name || ""} (${status})` : name || "";
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

    rememberBounds() {
        if (!this.map) {
            return;
        }
        const bounds = this.map.getBounds();
        this.state.bounds = {
            south: bounds.getSouth(),
            north: bounds.getNorth(),
            west: bounds.getWest(),
            east: bounds.getEast(),
        };
    }

    onSyncChange(ev) {
        this.state.syncList = ev.target.checked;
    }

    fleetClass(vehicle) {
        const classes = ["o_tms_map_fleet_row"];
        if (this.state.selectedVehicleId === vehicle.id) {
            classes.push("o_tms_map_selected");
        }
        return classes.join(" ");
    }

    sinceLabel(value) {
        if (!value) {
            return "";
        }
        const then = new Date(value.replace(" ", "T") + "Z");
        if (Number.isNaN(then.getTime())) {
            return value;
        }
        const minutes = Math.max(
            0,
            Math.round((Date.now() - then.getTime()) / 60000)
        );
        if (minutes < 60) {
            return _t("%s min", minutes);
        }
        const hours = Math.round(minutes / 60);
        if (hours < 48) {
            return _t("%s h", hours);
        }
        return _t("%s d", Math.round(hours / 24));
    }

    async loadFleet() {
        this.clearDrawn();
        this.markers = {};
        const teamId = this.fleetTeamId;
        if (!teamId) {
            this.state.vehicles = [];
            this.state.message = _t("Open this map from a team.");
            return;
        }
        const fleet = await this.orm.call("tms.order", "tms_map_fleet", [teamId]);
        const vehicles = await this.restrict(fleet, "fleet.vehicle");
        this.state.vehicles = vehicles;
        const points = [];
        for (const vehicle of vehicles) {
            if (!(vehicle.latitude || vehicle.longitude)) {
                continue;
            }
            const placed = marker([vehicle.latitude, vehicle.longitude], {
                icon: pin(modeIcon(vehicle.mode), vehicle.motion || "off"),
                title: this.pinTitle(vehicle.name, vehicle.motion),
                zIndexOffset: 500,
            });
            placed.bindPopup(this.vehiclePopup(vehicle));
            placed.on("click", () => {
                this.state.selectedVehicleId = vehicle.id;
            });
            placed.addTo(this.layer);
            this.markers[vehicle.id] = placed;
            points.push([vehicle.latitude, vehicle.longitude]);
        }
        this.fit(points);
        this.rememberBounds();
        if (!vehicles.length) {
            this.state.message = _t("This team has no vehicles.");
        }
    }

    focusFleet(vehicle) {
        this.state.selectedVehicleId = vehicle.id;
        const placed = this.markers[vehicle.id];
        if (!placed || !this.map) {
            return;
        }
        placed.openPopup();
        this.map.setView(placed.getLatLng(), Math.max(this.map.getZoom(), 8));
    }

    tripClass(trip) {
        const classes = ["o_tms_map_trip"];
        if (this.state.selectedTripIds.includes(trip.id)) {
            classes.push("o_tms_map_selected");
        }
        return classes.join(" ");
    }

    tripRange(trip) {
        if (trip.date_start && trip.date_end) {
            return `${trip.date_start} – ${trip.date_end}`;
        }
        return trip.date_start || trip.date_end || "";
    }

    onSelectSeveral(ev) {
        this.state.selectSeveral = ev.target.checked;
        if (!ev.target.checked && this.state.selectedTripIds.length > 1) {
            this.state.selectedTripIds = this.state.selectedTripIds.slice(0, 1);
            this.drawHistory();
        }
    }

    async loadHistory() {
        let trips = await this.orm.call("tms.order", "tms_map_trip_history", [], {
            vehicle_id: this.historyVehicleId || false,
        });
        trips = await this.restrict(trips, "tms.order");
        const visible = new Set(trips.map((trip) => trip.id));
        this.state.selectedTripIds = this.state.selectedTripIds.filter((id) =>
            visible.has(id)
        );
        this.state.history = trips;
        if (!this.state.selectedTripIds.length && trips.length) {
            this.state.selectedTripIds = [trips[0].id];
        }
        if (!trips.length) {
            this.clearDrawn();
            this.state.message = _t("No trips yet.");
            return;
        }
        await this.drawHistory();
    }

    async selectTrip(trip) {
        const current = this.state.selectedTripIds;
        if (this.state.selectSeveral) {
            if (current.includes(trip.id)) {
                this.state.selectedTripIds = current.filter((id) => id !== trip.id);
            } else {
                this.state.selectedTripIds = [...current, trip.id];
            }
        } else {
            this.state.selectedTripIds = [trip.id];
        }
        await this.drawHistory();
    }

    async drawHistory() {
        this.clearDrawn();
        const ids = this.state.selectedTripIds;
        if (!ids.length) {
            this.state.message = _t("Select a trip.");
            return;
        }
        const tracks = await this.orm.call(
            "tms.order",
            "tms_map_history_tracks",
            [ids]
        );
        const points = [];
        tracks.forEach((track, index) => {
            const color = HISTORY_COLORS[index % HISTORY_COLORS.length];
            if (track.origin) {
                this.addNamedPin(track.origin, "fa-sign-in");
                points.push([track.origin.latitude, track.origin.longitude]);
            }
            if (track.destination) {
                this.addNamedPin(track.destination, "fa-flag");
                points.push([
                    track.destination.latitude,
                    track.destination.longitude,
                ]);
            }
            if (track.path && track.path.length) {
                polyline(track.path, {color, weight: 4}).addTo(this.layer);
                for (const point of track.path) {
                    points.push(point);
                }
            }
        });
        this.fit(points);
        if (!points.length) {
            this.state.message = _t("The selected trips have no coordinates.");
        }
    }

    async loadHeatmap() {
        this.clearDrawn();
        let points;
        if (this.props.searchModelName === "fleet.vehicle") {
            const ids = await this.orm.search(
                "fleet.vehicle",
                this.props.searchDomain || []
            );
            points = await this.orm.call("tms.order", "tms_map_heatmap", [ids]);
        } else {
            points = await this.orm.call("tms.order", "tms_map_heatmap", []);
        }
        if (!points.length) {
            this.state.message = _t("No odometer positions yet.");
            return;
        }
        this.heat = heatLayer(points, {radius: 25, blur: 15, maxZoom: 12});
        this.heat.addTo(this.map);
        this.fit(points.map((point) => [point[0], point[1]]));
    }
}

registry.category("view_widgets").add("tms_map", {
    component: TmsUniversalMap,
    extractProps: ({attrs}) => ({
        mapMode: attrs.mode,
    }),
});
