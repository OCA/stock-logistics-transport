import {visitXML} from "@web/core/utils/xml";

export class TmsMapArchParser {
    parse(arch) {
        const info = {
            latitude: "partner_latitude",
            longitude: "partner_longitude",
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
        });
        return info;
    }
}
