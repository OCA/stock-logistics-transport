import {Component, onMounted, onWillUnmount, useRef, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {
    AmbientLight,
    BoxGeometry,
    Color,
    ConeGeometry,
    CylinderGeometry,
    DirectionalLight,
    Group,
    DoubleSide,
    LineBasicMaterial,
    LineSegments,
    Mesh,
    MeshBasicMaterial,
    MeshLambertMaterial,
    MeshStandardMaterial,
    PerspectiveCamera,
    PlaneGeometry,
    SRGBColorSpace,
    TextureLoader,
    Raycaster,
    Scene,
    Vector2,
    WebGLRenderer,
    WireframeGeometry,
} from "../lib/three.module.js";

const SPACE_COLOR = {
    empty: 0x7f9bb8,
    stackable: 0x2f7d4a,
    top_load: 0xc48a12,
    blocked: 0xa33b3b,
    taken: 0x5b4b8a,
};

export class LoadPlanner extends Component {
    static template = "tms_load_planner.LoadPlanner";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.viewport = useRef("viewport");
        this.state = useState({
            tripId: this.props.action.context.active_id || false,
            trip: {},
            pool: [],
            loose: [],
            assigned: [],
            selectedId: false,
            selected: false,
            looseHover: false,
            message: "",
        });
        this.renderer = null;
        this.frame = null;
        onMounted(() => this.start());
        onWillUnmount(() => this.stop());
    }

    async start() {
        if (!this.state.tripId) {
            return;
        }
        await this.reload();
        this.mountScene();
    }

    async reload() {
        const data = await this.orm.call("tms.order", "get_load_planner_data", [
            [this.state.tripId],
        ]);
        this.applyPlannerData(data);
    }

    applyPlannerData(data) {
        this.state.trip = data;
        this.state.assigned = data.assigned;
        this.state.pool = data.pool;
        this.state.loose = data.loose || [];
        if (this.scene) {
            this.drawSpaces(data);
            this.drawCargo();
        }
    }

    async backToTrip() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: this.state.trip.name || "Trip",
            res_model: "tms.order",
            res_id: this.state.tripId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    mountScene() {
        const host = this.viewport.el;
        if (!host) {
            return;
        }
        const trip = this.state.trip;
        this.scene = new Scene();
        this.scene.background = new Color(0xf6f7f9);
        const width = host.clientWidth || 800;
        const height = host.clientHeight || 480;
        const length = trip.length || 13.6;
        const boxHeight = trip.height || 2.7;
        const kind = this.bodyKind(trip);
        const deck = this.deckHeight(kind);
        this.camera = new PerspectiveCamera(45, width / height, 0.1, 400);
        this.camera.position.set(0, deck + boxHeight * 2.4, length * 1.45 + 12);
        this.camera.lookAt(-length * 0.12, deck + boxHeight * 0.35, 0);
        this.renderer = new WebGLRenderer({antialias: true, alpha: true});
        this.renderer.setSize(width, height);
        host.appendChild(this.renderer.domElement);
        this.bindDrag(host);
        this.scene.add(new AmbientLight(0xffffff, 0.75));
        const sun = new DirectionalLight(0xffffff, 0.85);
        sun.position.set(-12, 24, 10);
        this.scene.add(sun);
        this.rig = new Group();
        this.rig.rotation.y = 0.55;
        this.scene.add(this.rig);
        this.raycaster = new Raycaster();
        this.spaceMeshes = [];
        this.drawGround(kind, length);
        this.drawPlan(trip, deck);
        this.drawShell(trip, deck);
        this.drawBody(trip, kind, deck);
        this.drawCargo();
        const render = () => {
            this.frame = requestAnimationFrame(render);
            this.renderer.render(this.scene, this.camera);
        };
        render();
    }

    orientationHint() {
        const hints = {
            truck: "The cab is the front. The trailer behind it is the load.",
            box: "The cab is the front. The box behind the seats is the load.",
            van: "The windshield is the front. Cargo sits behind the seats.",
            bus: "The windshield is the front.",
            boat: "The bow is the front. The hold is the load.",
            plane: "The nose is the front. The tail is the rear.",
            train: "The locomotive is the front. The wagon is the load.",
        };
        return hints[this.bodyKind(this.state.trip)] || hints.truck;
    }

    bodyKind(trip) {
        const category = (trip.category || "").toLowerCase();
        if (/rail|train|wagon|locomotive/.test(category)) {
            return "train";
        }
        const type = trip.vehicle_type || "truck";
        if (type === "truck" && category.includes("box")) {
            return "box";
        }
        if (type === "car") {
            return "van";
        }
        return type;
    }

    deckHeight(kind) {
        if (kind === "boat") {
            return 0.9;
        }
        if (kind === "plane") {
            return 1.7;
        }
        if (kind === "train") {
            return 1.05;
        }
        return 1.15;
    }

    bindDrag(host) {
        host.addEventListener("pointerdown", (ev) => {
            const spaceId = this.spaceUnderPointer(ev);
            const allocation = this.allocationForSpace(spaceId);
            this.pointer = {
                x: ev.clientX,
                y: ev.clientY,
                spaceId,
                cargoId: allocation && allocation.cargo_id,
            };
            this.dragging = !this.pointer.cargoId;
            this.lastX = ev.clientX;
            host.setPointerCapture(ev.pointerId);
        });
        host.addEventListener("pointermove", (ev) => {
            if (this.pointer && this.pointer.cargoId) {
                return;
            }
            if (!this.dragging || !this.rig) {
                return;
            }
            this.rig.rotation.y += (ev.clientX - this.lastX) * 0.01;
            this.lastX = ev.clientX;
        });
        host.addEventListener("pointerup", (ev) => {
            const pointer = this.pointer;
            this.pointer = null;
            this.dragging = false;
            if (!pointer || !pointer.cargoId) {
                return;
            }
            const travel = Math.hypot(ev.clientX - pointer.x, ev.clientY - pointer.y);
            if (travel <= 6) {
                this.selectCargo(pointer.cargoId);
                return;
            }
            const spaceId = this.spaceUnderPointer(ev);
            if (spaceId && spaceId !== pointer.spaceId) {
                this.moveCargo(pointer.cargoId, spaceId);
            }
        });
    }

    allocationForSpace(spaceId) {
        const rows = this.state.trip.allocations || [];
        return rows.find((row) => row.space_id === spaceId);
    }

    placedCargo() {
        return this.state.assigned.filter((cargo) => cargo.space);
    }

    selectCargo(cargoId) {
        const lists = [this.state.assigned, this.state.loose, this.state.pool];
        let cargo = false;
        lists.forEach((rows) => {
            cargo = cargo || rows.find((row) => row.id === cargoId);
        });
        if (!cargo) {
            const allocation = (this.state.trip.allocations || []).find(
                (row) => row.cargo_id === cargoId
            );
            if (allocation) {
                cargo = {
                    id: cargoId,
                    name: allocation.cargo_name,
                    space: allocation.code,
                    weight: allocation.weight,
                    volume: allocation.volume,
                    quantity: allocation.quantity,
                    uom: allocation.uom,
                    weight_uom: allocation.weight_uom,
                    volume_uom: allocation.volume_uom,
                    packaging: allocation.packaging,
                    state_label: allocation.state_label,
                    is_stackable: allocation.is_stackable,
                };
            }
        }
        this.state.selectedId = cargo ? cargo.id : false;
        this.state.selected = cargo || false;
        if (this.scene) {
            this.drawSpaces(this.state.trip);
        }
        const card = document.querySelector(
            `.o_tms_load_planner [data-cargo-id="${this.state.selectedId}"]`
        );
        if (card) {
            card.scrollIntoView({block: "nearest"});
        }
    }

    paint(color, opacity = 1) {
        this.materials = this.materials || {};
        const key = `${color}:${opacity}`;
        if (!this.materials[key]) {
            this.materials[key] = new MeshStandardMaterial({
                color,
                transparent: opacity < 1,
                opacity,
                roughness: 0.55,
                metalness: 0.05,
            });
        }
        return this.materials[key];
    }

    addBox(group, width, height, depth, x, y, z, color, opacity = 1) {
        const mesh = new Mesh(
            new BoxGeometry(width, height, depth),
            this.paint(color, opacity)
        );
        mesh.position.set(x, y, z);
        group.add(mesh);
        return mesh;
    }

    addWheel(group, x, z, radius = 0.48) {
        const wheel = new Mesh(
            new CylinderGeometry(radius, radius, 0.32, 18),
            this.paint(0x1c1c1c)
        );
        wheel.rotation.x = Math.PI / 2;
        wheel.position.set(x, radius, z);
        group.add(wheel);
    }

    addAxle(group, x, span, radius = 0.48) {
        const side = span / 2 + 0.08;
        this.addWheel(group, x, -side, radius);
        this.addWheel(group, x, side, radius);
    }

    drawGround(kind, length) {
        const color = kind === "boat" ? 0xc5dde8 : 0xd9e0e8;
        const ground = new Mesh(new PlaneGeometry(length + 16, 16), this.paint(color));
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = -0.02;
        this.rig.add(ground);
    }

    slotPosition(trip, slot) {
        const length = trip.length || 13.6;
        const width = trip.width || 2.45;
        const height = trip.height || 2.7;
        return {
            x: slot.pos_x + slot.length / 2 - length / 2,
            y: slot.pos_z + slot.height / 2 - height / 2,
            z: slot.pos_y + slot.width / 2 - width / 2,
        };
    }

    drawPlan(trip, deck) {
        if (!trip.layout_image_url) {
            return;
        }
        const loader = new TextureLoader();
        loader.load(trip.layout_image_url, (texture) => {
            if (!this.rig) {
                return;
            }
            texture.colorSpace = SRGBColorSpace;
            const length = trip.length || 13.6;
            const width = trip.width || 2.45;
            const plan = new Mesh(
                new PlaneGeometry(length, width),
                new MeshBasicMaterial({map: texture, side: DoubleSide})
            );
            plan.rotation.x = -Math.PI / 2;
            plan.position.y = deck + 0.05;
            this.rig.add(plan);
        });
    }

    drawShell(trip, deck) {
        const length = trip.length || 13.6;
        const width = trip.width || 2.45;
        const height = trip.height || 2.7;
        const geometry = new BoxGeometry(length, height, width);
        const material = new MeshStandardMaterial({
            color: 0x8aa4c8,
            transparent: true,
            opacity: 0.18,
            wireframe: true,
        });
        this.shell = new Mesh(geometry, material);
        this.shell.position.y = deck + height / 2;
        this.rig.add(this.shell);
        this.cargoRoot = new Mesh();
        this.shell.add(this.cargoRoot);
        this.drawSpaces(trip);
    }

    drawBody(trip, kind, deck) {
        const length = trip.length || 13.6;
        const width = trip.width || 2.45;
        const height = trip.height || 2.7;
        const body = new Group();
        const front = -length / 2;
        const rear = length / 2;
        if (kind === "boat") {
            this.drawBoat(body, front, rear, width, height, deck);
        } else if (kind === "plane") {
            this.drawPlane(body, front, rear, width, height, deck);
        } else if (kind === "train") {
            this.drawTrain(body, front, rear, width, height, deck);
        } else if (kind === "bus") {
            this.drawBus(body, front, rear, width, height, deck);
        } else if (kind === "van" || kind === "box") {
            this.drawVan(body, front, rear, width, height, deck);
        } else {
            this.drawTruck(body, front, rear, width, height, deck);
        }
        this.rig.add(body);
    }

    drawTruck(body, front, rear, width, height, deck) {
        const cabLength = 2.5;
        const cabWidth = Math.min(width, 2.55);
        const cabHeight = Math.min(height, 3.1);
        const hood = 1.35;
        const cabX = front - 0.45 - cabLength / 2;
        this.addBox(
            body,
            rear - front,
            0.22,
            width * 0.72,
            0,
            deck - 0.12,
            0,
            0x3a414a
        );
        this.addBox(
            body,
            cabLength,
            cabHeight,
            cabWidth,
            cabX,
            0.5 + cabHeight / 2,
            0,
            0xf4f7fb
        );
        this.addBox(
            body,
            hood,
            1.45,
            cabWidth * 0.92,
            cabX - cabLength / 2 - hood / 2,
            1.2,
            0,
            0xe7edf3
        );
        this.addBox(
            body,
            0.08,
            cabHeight * 0.42,
            cabWidth * 0.86,
            cabX - cabLength / 2 + 0.02,
            0.5 + cabHeight * 0.72,
            0,
            0x6ea8c9
        );
        this.addAxle(body, cabX - 0.7, cabWidth, 0.5);
        this.addAxle(body, cabX + 0.85, cabWidth, 0.5);
        this.addAxle(body, rear - 1.3, width, 0.5);
        this.addAxle(body, rear - 2.7, width, 0.5);
        this.addBox(
            body,
            0.08,
            height * 0.92,
            width * 0.46,
            rear,
            deck + height * 0.5,
            -width * 0.24,
            0xd5dee6
        );
        this.addBox(
            body,
            0.08,
            height * 0.92,
            width * 0.46,
            rear,
            deck + height * 0.5,
            width * 0.24,
            0xd5dee6
        );
    }

    drawVan(body, front, rear, width, height, deck) {
        const cabLength = 1.8;
        const cabX = front - cabLength / 2 + 0.15;
        this.addBox(body, cabLength, height * 0.92, width * 0.98, cabX, deck + height * 0.42, 0, 0xf4f7fb);
        this.addBox(
            body,
            0.08,
            height * 0.38,
            width * 0.84,
            cabX - cabLength / 2 + 0.02,
            deck + height * 0.62,
            0,
            0x6ea8c9
        );
        this.addAxle(body, cabX - 0.35, width * 0.92, 0.42);
        this.addAxle(body, rear - 1.1, width * 0.92, 0.42);
        this.addBox(
            body,
            0.08,
            height * 0.8,
            width * 0.9,
            rear,
            deck + height * 0.45,
            0,
            0xd5dee6
        );
    }

    drawBus(body, front, rear, width, height, deck) {
        this.addBox(body, 0.55, height, width, front - 0.2, deck + height / 2, 0, 0xf4f7fb);
        this.addBox(
            body,
            0.08,
            height * 0.45,
            width * 0.9,
            front - 0.46,
            deck + height * 0.62,
            0,
            0x6ea8c9
        );
        this.addBox(
            body,
            rear - front,
            0.12,
            width * 1.02,
            0,
            deck + height + 0.06,
            0,
            0xdfe6ee
        );
        this.addBox(body, 0.4, height * 0.7, width, rear + 0.15, deck + height * 0.4, 0, 0xe7edf3);
        this.addAxle(body, front + 1.6, width, 0.48);
        this.addAxle(body, rear - 1.8, width, 0.48);
    }

    drawBoat(body, front, rear, width, height, deck) {
        const hullLength = rear - front;
        this.addBox(body, hullLength, 0.7, width * 1.08, 0, deck - 0.2, 0, 0xf7f8fa);
        const bowLength = Math.max(width * 0.55, 1.6);
        const bow = new Mesh(
            new ConeGeometry(width * 0.54, bowLength, 4),
            this.paint(0xf7f8fa)
        );
        bow.rotation.z = Math.PI / 2;
        bow.rotation.y = Math.PI / 4;
        bow.position.set(front - bowLength / 2, deck - 0.05, 0);
        body.add(bow);
        this.addBox(
            body,
            Math.min(4, hullLength * 0.22),
            height * 0.55,
            width * 0.55,
            rear - hullLength * 0.18,
            deck + height * 0.35,
            0,
            0xe7edf3
        );
    }

    drawPlane(body, front, rear, width, height, deck) {
        const nose = Math.max(2.4, width);
        const cone = new Mesh(new ConeGeometry(width * 0.42, nose, 16), this.paint(0xf7f8fa));
        cone.rotation.z = Math.PI / 2;
        cone.position.set(front - nose / 2, deck + height * 0.45, 0);
        body.add(cone);
        const span = Math.max(width * 4.5, 10);
        this.addBox(
            body,
            Math.max(3, (rear - front) * 0.18),
            0.18,
            span,
            front * 0.15,
            deck + height * 0.15,
            0,
            0xd5dee8
        );
        this.addBox(body, 0.7, height * 0.85, 0.18, rear + 0.2, deck + height * 0.85, 0, 0xf4f7fb);
        this.addBox(body, 1.4, 0.12, width * 2.2, rear + 0.15, deck + height * 0.55, 0, 0xf4f7fb);
        this.addWheel(body, front + 1.2, 0, 0.35);
        this.addWheel(body, rear * 0.15, width * 0.55, 0.35);
        this.addWheel(body, rear * 0.15, -width * 0.55, 0.35);
    }

    drawTrain(body, front, rear, width, height, deck) {
        const loco = 4.2;
        const locoX = front - 0.35 - loco / 2;
        this.addBox(body, loco, height * 0.82, width * 0.92, locoX, deck + height * 0.38, 0, 0xf4f7fb);
        this.addBox(
            body,
            0.08,
            height * 0.28,
            width * 0.7,
            locoX - loco / 2 + 0.02,
            deck + height * 0.55,
            0,
            0x6ea8c9
        );
        this.addAxle(body, locoX - 1.2, width * 0.8, 0.38);
        this.addAxle(body, locoX + 1.2, width * 0.8, 0.38);
        this.addAxle(body, front + 1.4, width * 0.8, 0.38);
        this.addAxle(body, rear - 1.4, width * 0.8, 0.38);
    }

    allocationBySpace(trip) {
        const rows = {};
        (trip.allocations || []).forEach((row) => {
            rows[row.space_id] = row;
        });
        return rows;
    }

    drawSpaces(trip) {
        (this.spaceMeshes || []).forEach((mesh) => mesh.removeFromParent());
        (this.spaceFrames || []).forEach((mesh) => mesh.removeFromParent());
        this.spaceMeshes = [];
        this.spaceFrames = [];
        const allocations = this.allocationBySpace(trip);
        (trip.spaces || []).forEach((slot) => {
            if (!slot.length || !slot.width || !slot.height) {
                return;
            }
            const allocation = allocations[slot.id];
            const state = allocation ? allocation.state : "available";
            const geometry = new BoxGeometry(slot.length, slot.height, slot.width);
            const position = this.slotPosition(trip, slot);
            const frame = this.allocationMesh(geometry, state, slot, allocation);
            frame.userData.spaceId = slot.id;
            if (this.allocationIsSelected(allocation)) {
                this.highlightSpace(frame, geometry);
            }
            frame.position.set(position.x, position.y, position.z);
            this.shell.add(frame);
            this.spaceMeshes.push(frame);
        });
    }

    allocationIsSelected(allocation) {
        return Boolean(
            allocation &&
                allocation.cargo_id &&
                Number(allocation.cargo_id) === Number(this.state.selectedId)
        );
    }

    highlightSpace(frame, geometry) {
        if (frame.material && frame.material.emissive) {
            frame.material = frame.material.clone();
            frame.material.emissive = new Color(0xf5c542);
            frame.material.emissiveIntensity = 0.45;
        }
        const outline = new LineSegments(
            new WireframeGeometry(geometry),
            new LineBasicMaterial({color: 0xf5c542, depthTest: false})
        );
        outline.scale.set(1.08, 1.08, 1.08);
        outline.renderOrder = 3;
        frame.add(outline);
    }

    allocationMesh(geometry, state, slot, allocation) {
        if (state === "booked") {
            return new Mesh(
                geometry,
                new MeshLambertMaterial({
                    color: (allocation && allocation.color) || SPACE_COLOR.stackable,
                })
            );
        }
        if (state === "blocked") {
            const mesh = new Mesh(geometry, new MeshLambertMaterial({color: 0x8d8d8d}));
            const wire = new LineSegments(
                new WireframeGeometry(geometry),
                new LineBasicMaterial({color: SPACE_COLOR.blocked})
            );
            mesh.add(wire);
            return mesh;
        }
        const status = slot.status || "empty";
        const wireColor =
            status === "blocked"
                ? SPACE_COLOR.blocked
                : status === "taken"
                  ? SPACE_COLOR.taken
                  : 0xd0d5dd;
        const hit = new Mesh(
            geometry,
            new MeshBasicMaterial({
                transparent: true,
                opacity: 0,
                depthWrite: false,
            })
        );
        const wire = new LineSegments(
            new WireframeGeometry(geometry),
            new LineBasicMaterial({color: wireColor})
        );
        wire.userData.spaceId = slot.id;
        hit.add(wire);
        this.spaceFrames.push(wire);
        return hit;
    }

    drawCargo() {
        if (!this.cargoRoot) {
            return;
        }
        while (this.cargoRoot.children.length) {
            this.cargoRoot.remove(this.cargoRoot.children[0]);
        }
        const trip = this.state.trip;
        if ((trip.allocations || []).length) {
            return;
        }
        this.state.assigned.forEach((cargo) => {
            if (!cargo.length || !cargo.width || !cargo.height) {
                return;
            }
            const piece = new Mesh(
                new BoxGeometry(
                    cargo.length * 0.72,
                    cargo.height * 0.72,
                    cargo.width * 0.72
                ),
                new MeshStandardMaterial({
                    color: SPACE_COLOR[cargo.status] || SPACE_COLOR.stackable,
                })
            );
            const position = this.slotPosition(trip, cargo);
            piece.position.set(position.x, position.y, position.z);
            this.cargoRoot.add(piece);
        });
    }

    spaceUnderPointer(ev) {
        const canvas = this.renderer && this.renderer.domElement;
        if (!canvas || !this.spaceMeshes.length) {
            return false;
        }
        const rect = canvas.getBoundingClientRect();
        const pointer = new Vector2(
            ((ev.clientX - rect.left) / rect.width) * 2 - 1,
            -((ev.clientY - rect.top) / rect.height) * 2 + 1
        );
        this.raycaster.setFromCamera(pointer, this.camera);
        const hits = this.raycaster.intersectObjects(this.spaceMeshes, false);
        return hits.length ? hits[0].object.userData.spaceId : false;
    }

    stop() {
        if (this.frame) {
            cancelAnimationFrame(this.frame);
        }
        if (this.renderer) {
            this.renderer.dispose();
        }
    }

    onDragStart(cargo, ev) {
        ev.dataTransfer.setData("text/plain", String(cargo.id));
        ev.dataTransfer.effectAllowed = "move";
    }

    onDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
    }

    onLooseDragOver(ev) {
        this.onDragOver(ev);
        this.state.looseHover = true;
    }

    onLooseDragLeave(ev) {
        const next = ev.relatedTarget;
        if (next && ev.currentTarget.contains(next)) {
            return;
        }
        this.state.looseHover = false;
    }

    async onDropLoose(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.state.looseHover = false;
        if (!this.state.tripId) {
            return;
        }
        const cargoId = Number.parseInt(ev.dataTransfer.getData("text/plain"), 10);
        if (!cargoId) {
            return;
        }
        await this.releaseCargo(cargoId);
    }

    async onDrop(ev) {
        ev.preventDefault();
        if (!this.state.tripId) {
            return;
        }
        const cargoId = Number.parseInt(ev.dataTransfer.getData("text/plain"), 10);
        const spaceId = this.spaceUnderPointer(ev);
        if (!cargoId || !spaceId) {
            this.state.message = "Drop the cargo on a space.";
            return;
        }
        await this.moveCargo(cargoId, spaceId);
    }

    async moveCargo(cargoId, spaceId) {
        try {
            const data = await this.orm.call("tms.order", "assign_load_planner_cargo", [
                [this.state.tripId],
                cargoId,
                spaceId,
            ]);
            this.state.message = "";
            this.applyPlannerData(data);
            this.selectCargo(cargoId);
        } catch (error) {
            this.state.message =
                (error.data && error.data.message) ||
                error.message ||
                "This cargo cannot use that space.";
        }
    }

    async releaseCargo(cargoId) {
        try {
            const data = await this.orm.call(
                "tms.order",
                "release_load_planner_cargo",
                [[this.state.tripId], cargoId]
            );
            this.state.message = "";
            this.applyPlannerData(data);
            this.selectCargo(cargoId);
        } catch (error) {
            this.state.message =
                (error.data && error.data.message) ||
                error.message ||
                "This cargo cannot leave its space.";
        }
    }
}

registry.category("actions").add("tms_load_planner", LoadPlanner);
