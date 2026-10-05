import {
    Component,
    onMounted,
    onWillUnmount,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {
    divIcon,
    featureGroup,
    map as createMap,
    marker,
    tileLayer,
} from "../../lib/leaflet-src.esm.js";

const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

function pin() {
    return divIcon({
        className: "",
        html: '<i class="fa fa-map-marker o_tms_map_icon"></i>',
        iconSize: [28, 28],
        iconAnchor: [14, 28],
    });
}

export class TmsMapViewRenderer extends Component {
    static template = "tms_map.TmsMapViewRenderer";
    static props = {
        model: Object,
        archInfo: Object,
        onOpen: Function,
    };

    setup() {
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

    signature() {
        const root = this.props.model.root;
        const records = (root && root.records) || [];
        const {latitude, longitude} = this.props.archInfo;
        return records
            .map((record) => {
                const data = record.data;
                return [record.resId, data[latitude], data[longitude]].join(":");
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
        const {latitude, longitude} = this.props.archInfo;
        const records = (this.props.model.root && this.props.model.root.records) || [];
        this.points = [];
        for (const record of records) {
            const lat = record.data[latitude];
            const lng = record.data[longitude];
            if (!(lat || lng)) {
                continue;
            }
            const name = record.data.display_name || "";
            const placed = marker([lat, lng], {icon: pin(), title: name});
            placed.on("click", () => this.props.onOpen(record.resId));
            placed.addTo(this.layer);
            this.points.push([lat, lng]);
        }
        this.state.message = this.points.length
            ? ""
            : _t("No coordinates on these locations.");
        this.refit();
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
