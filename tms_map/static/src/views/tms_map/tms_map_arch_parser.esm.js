import {visitXML} from "@web/core/utils/xml";

export class TmsMapArchParser {
    parse(arch) {
        const info = {
            latitude: "partner_latitude",
            longitude: "partner_longitude",
            mode: "",
            motion: "",
            shape: "",
            perimeter: "",
        };
        visitXML(arch, (node) => {
            if (node.tagName !== "tms_map") {
                return;
            }
            if (node.hasAttribute("latitude")) {
                info.latitude = node.getAttribute("latitude");
            }
            if (node.hasAttribute("longitude")) {
                info.longitude = node.getAttribute("longitude");
            }
            if (node.hasAttribute("mode")) {
                info.mode = node.getAttribute("mode");
            }
            if (node.hasAttribute("motion")) {
                info.motion = node.getAttribute("motion");
            }
            if (node.hasAttribute("shape")) {
                info.shape = node.getAttribute("shape");
            }
            if (node.hasAttribute("perimeter")) {
                info.perimeter = node.getAttribute("perimeter");
            }
        });
        return info;
    }
}
