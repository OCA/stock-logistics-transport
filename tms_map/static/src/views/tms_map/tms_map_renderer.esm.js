import {
    Component,
    onMounted,
    onWillUnmount,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {
    featureGroup,
    map as createMap,
    marker,
    polygon,
    tileLayer,
} from "../../lib/leaflet-src.esm.js";
import {
    GEOFENCE_STYLE,
    modeIcon,
    motionLabel,
    motionLegend as motionLegendItems,
    parsePerimeter,
    pin,
} from "../../tms_map_pin.esm.js";
import {drawTransportLocations} from "../../tms_map_locations.esm.js";

const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

export class TmsMapViewRenderer extends Component {
    static template = "tms_map.TmsMapViewRenderer";
    static props = {
        model: Object,
        archInfo: Object,
        onOpen: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.mapRef = useRef("map");
        this.state = useState({message: ""});
        this.map = null;
        this.layer = null;
        this.points = [];
        onMounted(() => this.start());
        onWillUnmount(() => this.stop());
        useEffect(
            () => {
                this.draw();
            },
            () => [this.signature()]
        );
    }

    get showMotionLegend() {
        return Boolean(this.props.archInfo.motion);
    }

    get motionLegend() {
        return motionLegendItems();
    }

    signature() {
        const root = this.props.model.root;
        const records = (root && root.records) || [];
        const {latitude, longitude, mode, motion} = this.props.archInfo;
        return records
            .map((record) => {
                const data = record.data;
                return [
                    record.resId,
                    data[latitude],
                    data[longitude],
                    mode ? data[mode] : "",
                    motion ? data[motion] : "",
                ].join(":");
            })
            .join("|");
    }

    start() {
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
        this.observer = new ResizeObserver(() => this.refit());
        this.observer.observe(element);
        this.draw();
    }

    stop() {
        if (this.observer) {
            this.observer.disconnect();
        }
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }

    draw() {
        if (!this.map || !this.layer) {
            return;
        }
        this.layer.clearLayers();
        const {latitude, longitude, mode, motion, shape, perimeter} =
            this.props.archInfo;
        const records = (this.props.model.root && this.props.model.root.records) || [];
        this.points = [];
        for (const record of records) {
            const name = record.data.display_name || "";
            if (shape && record.data[shape] === "area") {
                const corners = parsePerimeter(record.data[perimeter]);
                if (corners.length >= 3) {
                    const area = polygon(corners, GEOFENCE_STYLE).addTo(this.layer);
                    area.on("click", () => this.props.onOpen(record.resId));
                    if (name) {
                        area.bindTooltip(name);
                    }
                    this.points.push(...corners);
                }
                continue;
            }
            if (shape && record.data[shape] !== "point") {
                continue;
            }
            const lat = record.data[latitude];
            const lng = record.data[longitude];
            if (!(lat || lng)) {
                continue;
            }
            const iconClass = mode ? modeIcon(record.data[mode]) : "fa-map-marker";
            const status = motion ? record.data[motion] || "off" : false;
            const label = motionLabel(status);
            const title = label ? `${name} (${label})` : name;
            const placed = marker([lat, lng], {
                icon: pin(iconClass, status),
                title,
            });
            placed.on("click", () => this.props.onOpen(record.resId));
            placed.addTo(this.layer);
            this.points.push([lat, lng]);
        }
        this.state.message = this.points.length
            ? ""
            : _t("No coordinates to show.");
        this.refit();
        this.overlayLocations();
    }

    async overlayLocations() {
        if (!this.locations || this.props.archInfo.shape) {
            return;
        }
        const rows = await this.orm.call("res.partner", "tms_map_locations", []);
        if (!this.locations) {
            return;
        }
        drawTransportLocations(this.locations, rows);
        if (rows.length) {
            this.state.message = "";
        }
    }

    refit() {
        if (!this.map) {
            return;
        }
        this.map.invalidateSize();
        if (!this.points.length) {
            return;
        }
        if (this.points.length === 1) {
            this.map.setView(this.points[0], 12);
            return;
        }
        this.map.fitBounds(this.points, {padding: [24, 24]});
    }
}
