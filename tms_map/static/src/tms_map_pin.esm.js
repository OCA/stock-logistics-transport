import {_t} from "@web/core/l10n/translation";
import {divIcon} from "./lib/leaflet-src.esm.js";

export const MODE_ICON = {
    air: "fa-plane",
    water: "fa-ship",
    road: "fa-truck",
    rail: "fa-train-subway",
};

const MOTION_CLASS = {
    moving: "o_tms_map_moving",
    idle: "o_tms_map_idle",
    off: "o_tms_map_off",
};

export const GEOFENCE_STYLE = {
    color: "#1f4e79",
    weight: 2,
    fillColor: "#1f4e79",
    fillOpacity: 0.18,
};

export function parsePerimeter(value) {
    let corners = value;
    if (!corners) {
        return [];
    }
    if (typeof corners === "string") {
        try {
            corners = JSON.parse(corners);
        } catch {
            return [];
        }
    }
    if (!Array.isArray(corners)) {
        return [];
    }
    return corners.filter(
        (pair) => Array.isArray(pair) && pair.length >= 2 && (pair[0] || pair[1])
    );
}

export function modeIcon(mode) {
    return MODE_ICON[mode] || MODE_ICON.road;
}

export function motionLabel(motion) {
    const labels = {
        moving: _t("On, moving"),
        idle: _t("On, stopped"),
        off: _t("Off"),
    };
    return labels[motion] || "";
}

export function motionLegend() {
    return ["moving", "idle", "off"].map((motion) => ({
        motion,
        label: motionLabel(motion),
    }));
}

export function pin(iconClass, motion) {
    const status = MOTION_CLASS[motion] || "";
    const classes = ["fa", iconClass, "o_tms_map_icon", status]
        .filter(Boolean)
        .join(" ");
    return divIcon({
        className: "",
        html: `<i class="${classes}"></i>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
}

export function vehiclePinClass(vehicle) {
    const status = MOTION_CLASS[vehicle.motion] || MOTION_CLASS.off;
    return ["fa", modeIcon(vehicle.mode), "o_tms_map_icon", status]
        .filter(Boolean)
        .join(" ");
}
