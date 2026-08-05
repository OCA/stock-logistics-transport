# TMS Extensions — Logic Design & Domain Ontology

> **Status:** Draft 0.2 — contribution to **`OCA/stock-logistics-transport`**, branch `19.0`
> **Scope (MVP):** `tms_document` (generic document framework) → `l10n_tr_tms_document` (K/SRC/compliance) → `tms_adr` (dangerous goods).
> **Deferred (post-MVP):** assignment/movement, account/margin, international (CMR/TIR), cold-chain, AETR, and the Turkish e-document suite (`l10n_tr_tms_ewaybill`, `l10n_tr_tms_efatura`) — the latter to be built as an orchestration layer over **Nilvera** (or another GİB Özel Entegratör), not as a parallel GİB submission engine.
> **License:** Module code **AGPL-3.0-or-later** (matches the repo). This document: CC-BY-SA-4.0.
> **Audience:** OCA contributors extending the existing `tms` core; ontology engineers consuming the OWL artifact.

---

## 0. How to read this document

This is the specification for **extensions** to the official OCA Transport Management System. It does **not** redefine the existing core — it builds on it. Three layers:

1. **Analysis** (§1–§3) — the two reference systems (the OCA `tms` core we extend, and the legacy private `vsl_transport` that inspired the scope), plus the Turkish road-freight domain.
2. **Design** (§4–§9) — what the core already provides (§4.1), what our three MVP modules add (§4.2), the state machines, business rules, and module specs.
3. **Ontology** (§10) — a formal OWL 2 DL artifact (Turtle) re-expressing the domain, aligned to the real model names.

Turkish domain terms are kept and translated on first use.

---

## 1. Reference systems

### 1.1 The base we extend — OCA `stock-logistics-transport` (`19.0`)

Our work is a contribution to `OCA/stock-logistics-transport`. The repo already contains a TMS suite by **Open Source Integrators** (AGPL-3, `development_status: Alpha`):

- **`tms`** (core app): `tms.order`, `tms.driver`, `tms.route`, `tms.crew`, `tms.team`, `tms.stage`, `tms.insurance`, plus extensions of `fleet.vehicle` and `res.partner`, and `res.config.settings`.
- **`tms_account`, `tms_expense`, `tms_product`, `tms_purchase`, `tms_sale`** (commercial siblings).

What the existing core provides (verified by reading `tms/models/`):

- **`tms.order`** — a trip: `origin_id`/`destination_id` (res.partner flagged `tms_location`), optional `route_id`, `driver_id`, `vehicle_id`, `tms_team_id`, `crew_id`, scheduled/actual dates and durations, and a **`stage_id`** (kanban). Lifecycle is driven by stages plus two buttons: `button_start_order` / `button_end_order`.
- **`tms.stage`** — generic kanban stage (`stage_type ∈ {driver, order}`, `sequence`, `is_completed`, `is_default`, custom color, fold). **This is the lifecycle mechanism — there is no hardcoded state machine.**
- **`tms.driver`** — `_inherits res.partner` (a driver *is* a partner); inline license fields `driver_license_number`, `driver_license_type` (A/B/C/D — US-centric), `driver_license_expiration_date`, `driver_license_file`; `is_external`; its own `stage_id`. Contains a literal `# TODO: ADD A LICENCE MODEL`.
- **`fleet.vehicle` (extended)** — `tms_team_id`, `tms_driver_id`, `operation` (cargo/passenger), `capacity` + `cargo_uom_id`, `insurance_id` (m2m `tms.insurance`).
- **`res.partner` (extended)** — `tms_location` (marks transport locations), `location_type`.
- `button_start_order` already performs **inline** expiry checks: vehicle insurance (`tms.default_vehicle_insurance_security_days`) and driver license (`tms.default_driver_license_security_days`). This is exactly the seam our `tms_document` generalizes.

What the core **lacks** (our openings):
- A **generic document-expiry framework** — license/insurance today are inline fields on two models; there is no reusable, polymorphic document model. The driver file even carries a TODO for a license model.
- **Dangerous-goods (ADR)** support — no UN numbers, no ADR class, no vehicle/driver ADR-approval enforcement.
- **Turkish compliance** — no K1/K2/K3, R1, SRC1-4, psychotechnic, vehicle inspection; no e-Fatura/e-İrsaliye; license types are US (A/B/C/D), not the Turkish/European scheme (B, C1, C1E, C, CE, …).
- Multi-stop routes, partial loads, goods lines, capacity-vs-load validation, and driving-time (AETR) compliance. *(Out of MVP scope; revisited in §9.)*

### 1.2 The purpose reference — legacy `vsl_transport`

The private module `vsl_transport` (`volkantasci/vsl-tms-odoo`) is the **purpose reference**, not the code. It proved the value of: end-to-end order lifecycle; multi-stop + partial loads; dual own-fleet/external-carrier model; document expiry as a first-class concept; bidirectional invoicing; and the Turkish vehicle vocabulary (*Kamyonet, 6/10 Teker, 40 Ayak, Çekici, Dorse, Tenteli/Tentesiz, Frigo, HGS/OGS*). Its defects (monolithic, hardcoded Turkish UI, manual `amount_total`, `unlink()`-based re-invoicing, etc.) are documented in `git` history and **are not carried over**.

### 1.3 Design principles for the extensions

1. **Extend, never fork the core.** Reuse `tms.order`, `tms.driver`, `tms.stage`, `fleet.vehicle`. We add models and inherit existing ones; we do not redefine them.
2. **Stages remain the lifecycle.** Where we need lifecycle semantics (document validity), we use a dedicated state machine on our own models, not a parallel order FSM.
3. **Generalize, then specialize.** `tms_document` is a jurisdiction-neutral, polymorphic document framework; `l10n_tr_tms_document` adds the Turkish document types; nothing TR-specific leaks into the core.
4. **Compliance blocks operations.** Expired critical documents and ADR non-conformance must prevent `button_start_order` — reusing the existing seam.
5. **OCA-grade.** AGPL-3, copier/pre-commit/CI clean, translatable, multi-company safe, every model tested.

---

## 2. Turkey road-freight domain primer

*(Unchanged from the operational reality; summarized.)* Turkey's road-freight market is regulated by **UDH** (operational: carrier authorization K1/K2/K3, R1; driver qualification SRC; vehicle approval) and **GİB** (fiscal: e-Fatura, e-Arşiv, e-İrsaliye). It mixes **own-fleet** (*öz mal*), **contracted** (*sözleşmeli*) and **spot** (*sözleşmesiz*) carriers, so resource ownership is first-class.

### 2.1 Documents a compliant shipment touches

- **Fiscal (GİB):** e-Fatura, e-Arşiv, **e-İrsaliye** (legally binding waybill — goods may not move without one), e-MM. *(MVP-relevant only conceptually; e-doc modules deferred to the Nilvera decision.)*
- **Operational authorization (UDH):** **K1/K2/K3** (domestic goods carrier), **R1** (international), **SRC1-4** (driver professional qualification; SRC4 = dangerous goods/ADR-aligned), **psikoteknik**, **araç muayenesi** (periodic technical inspection).
- **Specialized:** **ADR** certificates (vehicle + driver), **CMR** (international), **TIR** carnet, **takograf** (tachograph for AETR).

### 2.2 Vocabulary (abbreviated)

Sevkiyat (shipment), Yükleme/Boşaltma (loading/unloading), Çekici (tractor), Dorse (trailer; Tenteli/Tentesiz/Kapalı/Açık/Frigo/Damperli/Lowbed), Kamyon (>3.5t rigid), Kamyonet (≤3.5t), Tonaj (tonnage), Parsiyel (LTL), Full/Komple (FTL), Güzergah (route), Plaka (`34 ABC 123`), HGS/OGS (toll), Vergi Dairesi/No (tax office/number).

### 2.3 ADR (dangerous goods)

UN hazard classes **1–9**, packing groups **I/II/III**, tunnel-restriction codes. A dangerous-goods movement requires an **ADR-approved vehicle**, **ADR-approved equipment**, and a driver holding **SRC4 / ADR certificate**.

---

## 3. Requirements & actors

### 3.1 Roles

The OCA `tms` core already defines security groups under a TMS category (e.g. `tms.group_tms_*`). Our modules reuse them and add one compliance group only if needed:

| Group | Can |
|---|---|
| `tms.group_tms_user` (existing) | Read/create own orders, drivers, vehicles. |
| `tms.group_tms_manager` (existing) | Full configuration, documents, deletion. |
| `tms.group_tms_compliance` (new, in `l10n_tr_tms_document`) | Manage K/SRC certificates, verify UMTS references. |

### 3.2 MVP functional requirements

| # | Requirement | Module |
|---|---|---|
| R1 | Attach **multiple, typed documents** to a driver, vehicle, (and any holder) with issue/expiry dates and a file. | `tms_document` |
| R2 | Compute document **validity** (`valid / expiring / expired`) from `expiry_date` + a configurable horizon, using `fields.Date.context_today`. | `tms_document` |
| R3 | Make `button_start_order` **block** when a *critical* document on the order's driver or vehicle is `expired` (generalizing the existing inline license/insurance check). | `tms_document` |
| R4 | Add Turkish document types — **K1/K2/K3, R1, SRC1-4, psychotechnic, vehicle inspection** — with issuing authority and UMTS verification reference. | `l10n_tr_tms_document` |
| R5 | Block hire/reward trips when the carrier lacks an active **K/R** certificate. | `l10n_tr_tms_document` |
| R6 | Declare dangerous goods on order lines (UN number, packing group, ADR class, tunnel code). | `tms_adr` |
| R7 | **Block `button_start_order`** when an ADR order's vehicle/driver are not ADR-approved (incl. driver SRC4). | `tms_adr` |

### 3.3 Deferred (post-MVP, listed for context)

Multi-stop routes & partial loads, capacity-vs-load validation, assignment/movement model, account/margin, international (CMR/TIR/customs), cold-chain, AETR, and the Turkish e-document suite (Nilvera orchestration).

---

## 4. Domain model

### 4.1 Existing OCA `tms` core (as-is — we inherit, not redefine)

```
tms.order
 ├─ name (seq "TMS/…"), company_id
 ├─ origin_id / destination_id  → res.partner (tms_location=True)
 ├─ route_id → tms.route ;  driver_id → tms.driver ;  vehicle_id → fleet.vehicle
 ├─ tms_team_id → tms.team ;  crew_id → tms.crew
 ├─ stage_id → tms.stage   ← lifecycle (kanban), NOT a fixed FSM
 ├─ scheduled_date_start/end, scheduled_duration ; date_start/end, duration
 ├─ button_start_order()  ← checks vehicle insurance + driver license expiry (inline)
 └─ button_end_order()

tms.driver   (_inherits res.partner)
 ├─ driver_license_number / driver_license_type (A/B/C/D) / driver_license_expiration_date / driver_license_file
 ├─ is_external, is_active, stage_id
 └─ # TODO: ADD A LICENCE MODEL   ← opening for tms_document

fleet.vehicle (extended)
 ├─ tms_driver_id, tms_team_id, operation{cargo,passenger}
 ├─ capacity + cargo_uom_id
 └─ insurance_id (m2m tms.insurance)

tms.stage   (stage_type ∈ {driver, order}; sequence; is_completed; is_default)
tms.route, tms.crew, tms.team, tms.insurance
res.partner  += tms_location, location_type
```

### 4.2 Our extensions (MVP)

#### `tms_document` — generic document framework

A single polymorphic, expiry-tracked document model. **Replaces the idea of duplicating a document model per holder** and generalizes the inline license/insurance checks.

```
tms.document
 ├─ res_model / res_id            polymorphic holder (tms.driver, fleet.vehicle, …)
 ├─ res_ref           Reference (computed)  → the holder record, for convenience/links
 ├─ doc_type          Selection  (extensible: license, insurance, inspection, adr_vehicle, …)
 ├─ name / reference  Char       (e.g. "SRC2-123456")
 ├─ issue_date / expiry_date     Date
 ├─ datas             Binary (attachment=True, widget=binary)   ← the file
 ├─ state             Selection {valid, expiring, expired}  (compute, NOT stored)
 ├─ critical          Boolean    ← if true, expiry blocks button_start_order
 ├─ active            Boolean    ← archive instead of delete
 ├─ notes             Text
 └─ company_id
```

**Validity compute** (`fields.Date.context_today(self)`; horizon from `ir.config_parameter` `tms.document.expiry_horizon_days`, default 30):
- `expiry_date` and `expiry_date < today − horizon`? → we keep it simple: `< today` ⇒ `expired`; within horizon ⇒ `expiring`; else `valid`. *(Exact threshold semantics finalized in the TDD plan.)*

**Hook into the core:** `_tms_document_check_critical(holder)` returns the set of expired critical documents. `tms.order.button_start_order` is **extended via `super()`** to call it for `driver_id` and `vehicle_id`; the legacy inline checks remain as a fallback/are superseded gracefully (no breaking change to existing fields).

#### `l10n_tr_tms_document` — Turkish compliance documents

Specializes `tms.document` with TR document types and the hire/reward carrier rule.

```
tms.document  (extended)
 ├─ doc_type ∈ {k1, k2, k3, r1, r2, src1, src2, src3, src4,
 │              psychotechnic, vehicle_inspection, adr_vehicle, adr_driver}
 ├─ issuing_authority      Char   (UDH / TOBB / GİB)
 └─ verification_reference Char   (UMTS / integrator ref)
 + seed data: document types; config param for horizon per type if needed
 + guard (BR-10): carrier executing hire/reward ⇒ active K (domestic) / R1 (intl) certificate
```

> Note on the existing inline driver license: `tms.driver.driver_license_*` stays intact for backward compatibility; `l10n_tr_tms_document` can additionally create a `tms.document(doc_type=src2/adr_driver)` record so the rich framework governs compliance.

#### `tms_adr` — dangerous goods

Declares dangerous goods and enforces ADR approval. **Depends on `tms` + `tms_document`** (ADR vehicle/driver approval is modeled as critical `tms.document` records: `adr_vehicle`, `adr_driver`/SRC4).

```
tms.un.number     — code, proper_shipping_name, adr_class_id, packing_group, tunnel_code
tms.adr.class     — code (1..9), name, label_image
tms.order.adr_line (new)  OR  extend order with a one2many of dangerous-goods items:
 ├─ order_id → tms.order
 ├─ un_number_id → tms.un.number
 ├─ quantity / packaging
 └─ notes
fleet.vehicle  += adr_approved (Boolean)  + critical tms.document(adr_vehicle)
tms.driver     += holds ADR/SRC4 verified via critical tms.document(adr_driver)
guard (BR-6): if order has adr_line ⇒ vehicle.adr_approved ∧ driver ADR-cert, else block start
```

---

## 5. State machines

### 5.1 `tms.order` lifecycle — **stages** (existing core)

The core uses kanban `tms.stage` (`stage_type='order'`). Typical stages: *New → Confirmed → In Progress → Done (+ Cancelled)*. Transitions are stage changes plus `button_start_order` / `button_end_order`. Our modules **do not add a parallel FSM**; they add **guards on `button_start_order`** (see §6).

### 5.2 `tms.document` validity — our state machine

```
                         (expiry − horizon ≤ today)         (expiry < today)
   valid ──────────────────────────────────────▶ expiring ─────────────────▶ expired
     ▲                                                                              │
     └──────────────── renewed (new issue_date / expiry_date in the future) ◀───────┘
```
- `expiring` horizon configurable (default 30 days).
- `expired` + `critical=True` ⇒ blocks `button_start_order` for the holder's active order.

> **Note:** `state` is a **non-stored** computed field — it is derived from `expiry_date` on read. Filters/domains must search on `expiry_date` (and the configured horizon), never on `state`.

### 5.3 `tms.driver` / `fleet.vehicle` — stages (existing); document checks layered on top.

---

## 6. Business rules & constraints

Each rule: `(B)` blocks an operation, `(W)` warns. Guards attach to the existing `button_start_order` via `super()`.

| # | Rule | Effect | Module |
|---|---|---|---|
| BR-D1 | A document's `state` is `expired` iff `expiry_date < today`. | invariant | `tms_document` |
| BR-D2 | `state='expiring'` iff `today ≤ expiry_date < today+horizon`. | invariant | `tms_document` |
| BR-D3 | `button_start_order` blocked if any **critical** document of `driver_id` or `vehicle_id` is `expired`. | (B) start | `tms_document` |
| BR-TR1 | Carrier on a hire/reward order must hold a non-expired **K1/K2/K3** (domestic) or **R1** (international) certificate (`critical`). | (B) start | `l10n_tr_tms_document` |
| BR-A1 | An order with an ADR line requires `vehicle.adr_approved` AND an `adr_vehicle` critical document. | (B) start | `tms_adr` |
| BR-A2 | An order with an ADR line requires the driver to hold an `adr_driver` (or SRC4) critical document. | (B) start | `tms_adr` |
| BR-A3 | ADR class, packing group and tunnel code are derived from the chosen `tms.un.number` (consistency). | invariant | `tms_adr` |

> **Migration note:** the existing inline checks in `button_start_order` (insurance via `tms.default_vehicle_insurance_security_days`, license via `tms.default_driver_license_security_days`) are preserved as the default behavior; `tms_document` adds the richer, multi-document path on top, so installing it is strictly additive.

---

## 7. End-to-end workflows (MVP)

### 7.1 Document-driven compliance (domestic)
1. Garage creates `tms.driver` + `fleet.vehicle`; attaches `tms.document` records: license, SRC2, psychotechnic (driver); insurance, inspection (vehicle) — each marked `critical` where appropriate.
2. Dispatcher creates `tms.order`, sets driver + vehicle, moves to a "Confirmed" stage.
3. Pressing **Start** (`button_start_order`) runs BR-D3 (and, with `l10n_tr_tms_document`, BR-TR1). Expired critical doc ⇒ `UserError` naming the document; order cannot start.
4. Renew the document (new expiry) ⇒ state returns to `valid`/`expiring` ⇒ Start succeeds.

### 7.2 Dangerous goods (ADR)
1. Add an ADR line to the order (UN number, e.g. UN 1203 petrol, class 3).
2. Assign an ADR-approved vehicle + driver with SRC4/ADR certificate (critical `tms.document`).
3. **Start** runs BR-D3 + BR-A1 + BR-A2. Non-conformance ⇒ `UserError`; otherwise the trip proceeds.

---

## 8. Module specifications (MVP) — build order

| # | Module | Depends on | Adds | OCA manifest |
|---|---|---|---|---|
| 1 | **`tms_document`** | `tms` | `tms.document` (polymorphic, expiry), horizon config param, `button_start_order` guard (BR-D1..D3). | license `AGPL-3`, author `Odoo Community Association (OCA)`, website `https://github.com/OCA/stock-logistics-transport`, `development_status: Beta`, `maintainers: ["volkantasci"]`. |
| 2 | **`l10n_tr_tms_document`** | `tms_document` | TR doc types (K1/K2/K3, R1, SRC1-4, psychotechnic, muayene), seed data, BR-TR1. | as above; `category: Localization/Turkey`. |
| 3 | **`tms_adr`** | `tms`, `tms_document` | `tms.un.number`, `tms.adr.class`, ADR order lines, `adr_approved` on vehicle, BR-A1..A3. | as above; `category: TMS`. |

Each module: own `__manifest__.py`, `models/`, `views/`, `security/ir.model.access.csv`, `data/`, `tests/test_*.py`, `i18n/<module>.pot`, `static/description/{icon.png,index.html}`, `readme/` fragments (OCA `README.md` is generated from these by copier).

---

## 9. Deferred modules (post-MVP — design only, not built now)

Listed so the ontology (§10) covers them; each becomes its own plan when scheduled.

- **`tms_assignment`** (movement, capacity & license-compat guards) — note the core's "max 2" must be reinterpreted as tractor+trailer = one movement.
- **`tms_account`** — already exists in OCA; we extend for carrier cost lines & margin, removing the legacy `unlink()` re-invoice antipattern.
- **`tms_international`** — CMR, TIR, customs, border crossings; R1 requirement (BR-TR1 generalizes).
- **`tms_coldchain`** — refrigerated equipment, temperature ranges & logs; delivery compliance.
- **`tms_aetr`** — tachograph import, AETR limits as start guards.
- **`l10n_tr_tms_ewaybill`** + **`l10n_tr_tms_efatura`** — **orchestration layer over Nilvera** (GİB transmission stays with the integrator); they auto-create invoice/waybill *records* from shipment data, enforce the e-İrsaliye-before-departure rule (BR-EW1), and keep the shipment↔e-document audit trail. Decided to defer until the Nilvera connector approach is confirmed.

---

## 10. Formal OWL ontology

### 10.1 Scope

OWL 2 DL artifact re-expressing §4–§6, aligned to the **real OCA model names** (`tms:Order`, `tms:Driver`, `tms:Stage`, `fleet:Vehicle`, plus our `tms:Document`, `tms:AdrClass`, `tms:UNNumber`). IRI namespace `https://odoo-tms.org/ontology/tms#` (placeholder). Reuses `owl`, `rdfs`, `xsd`, `dcterms`.

### 10.2 Class hierarchy (summary)

```
Thing
├── tms:Party (res.partner)  ⊇ tms:Customer, tms:Carrier, tms:Consignor, tms:Consignee
├── tms:Driver               (= tms.driver, _inherits res.partner)
├── tms:Vehicle              (= fleet.vehicle)  ⊇ tms:OwnVehicle, tms:ExternalVehicle
├── tms:Order                (= tms.order)
├── tms:Stage                (= tms.stage)
├── tms:Route                (= tms.route)
├── tms:Document             (tms.document — NEW)  ⊇ tms:CriticalDocument
│     ⊇ tms:LicenseDocument, tms:InsuranceDocument, tms:ADRDocument,
│       tms:CarrierCertificate (K1/K2/K3/R1), tms:DriverCertificate (SRC1-4)
├── tms:UNNumber, tms:ADRClass   (NEW)
├── tms:Location
```

### 10.3 Object properties (selected)

| Property | Domain → Range |
|---|---|
| `tms:hasDriver` / `tms:hasVehicle` | Order → Driver / Vehicle |
| `tms:hasStage` | Order → Stage |
| `tms:hasDocument` | (Driver ∪ Vehicle ∪ Carrier) → Document |
| `tms:hasUNNumber` | ADR line → UNNumber |
| `tms:hasClass` | UNNumber → ADRClass |
| `tms:issuedBy` | Document → Party |

### 10.4 Data properties (selected)

| Property | Range | On |
|---|---|---|
| `tms:expiryDate` | xsd:date | Document |
| `tms:documentState` | enum {valid, expiring, expired} | Document |
| `tms:critical` | xsd:boolean | Document |
| `tms:licenseClass` | enum {B,C1,C1E,C,CE,D1,D1E,D,DE} | Driver |
| `tms:capacity` | xsd:decimal | Vehicle |
| `tms:unNumber` | xsd:string | UNNumber |
| `tms:adrApproved` | xsd:boolean | Vehicle |

### 10.5 Axioms (plain English → formal)

1. A document is `expired` iff `expiryDate < today`. *(time-aware; modelled via a dated individual / SWRL in practice.)*
2. `CriticalDocument ⊑ Document`. A `CriticalDocument` whose `documentState = expired` and which `hasDocument`-belongs to a driver/vehicle of an order makes that order **non-startable** (realized as the `button_start_order` guard, BR-D3).
3. An order carrying an ADR line requires `∀hasVehicle.(adrApproved = true)` and a driver holding an ADR `CriticalDocument` (BR-A1, BR-A2).
4. `OwnVehicle ⊓ ExternalVehicle ⊑ ⊥` (disjoint).
5. Every document is `issuedBy exactly 1` party.

### 10.6 Turtle serialization (canonical artifact)

```turtle
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix :     <https://odoo-tms.org/ontology/tms#> .

<https://odoo-tms.org/ontology/tms> a owl:Ontology ;
    dct:title    "TMS Extensions Ontology"@en ;
    dct:description "Documents, ADR and Turkish compliance over the OCA tms core."@en ;
    owl:versionInfo "0.2.0" .

# ───────── Classes (core, aligned to OCA model names) ─────────
:Party        a owl:Class .
:Carrier      a owl:Class ; rdfs:subClassOf :Party .
:Driver       a owl:Class .           # tms.driver (_inherits res.partner)
:Vehicle      a owl:Class .           # fleet.vehicle
:OwnVehicle   a owl:Class ; rdfs:subClassOf :Vehicle .
:ExternalVehicle a owl:Class ; rdfs:subClassOf :Vehicle .
:Order        a owl:Class .           # tms.order
:Stage        a owl:Class .           # tms.stage
:Route        a owl:Class .           # tms.route
:Location     a owl:Class .

# ───────── Classes (NEW: documents & ADR) ─────────
:Document            a owl:Class .
:CriticalDocument    a owl:Class ; rdfs:subClassOf :Document .
:LicenseDocument     a owl:Class ; rdfs:subClassOf :Document .
:InsuranceDocument   a owl:Class ; rdfs:subClassOf :Document .
:ADRDocument         a owl:Class ; rdfs:subClassOf :CriticalDocument .
:CarrierCertificate  a owl:Class ; rdfs:subClassOf :CriticalDocument .  # K1/K2/K3, R1
:DriverCertificate   a owl:Class ; rdfs:subClassOf :CriticalDocument .  # SRC1-4, ADR driver
:UNNumber            a owl:Class .
:ADRClass            a owl:Class .

# ── Disjointness ──
:OwnVehicle  owl:disjointWith :ExternalVehicle .

# ───────── Object properties ─────────
:hasDriver    a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain :Order ; rdfs:range :Driver .
:hasVehicle   a owl:ObjectProperty ; rdfs:domain :Order ; rdfs:range :Vehicle .
:hasStage     a owl:ObjectProperty ; rdfs:domain :Order ; rdfs:range :Stage .
:hasDocument  a owl:ObjectProperty ; owl:inverseOf :documentOf ; rdfs:range :Document .
:issuedBy     a owl:ObjectProperty ; rdfs:domain :Document ; rdfs:range :Party .
:hasUNNumber  a owl:ObjectProperty ; rdfs:range :UNNumber .
:hasClass     a owl:ObjectProperty ; rdfs:domain :UNNumber ; rdfs:range :ADRClass .

# ───────── Data properties ─────────
:expiryDate     a owl:DatatypeProperty ; rdfs:domain :Document ; rdfs:range xsd:date .
:documentState  a owl:DatatypeProperty ; rdfs:domain :Document ;
   rdfs:range [ a rdfs:Datatype ; owl:oneOf ("valid" "expiring" "expired") ] .
:critical       a owl:DatatypeProperty ; rdfs:domain :Document ; rdfs:range xsd:boolean .
:licenseClass   a owl:DatatypeProperty ; rdfs:domain :Driver ;
   rdfs:range [ a rdfs:Datatype ; owl:oneOf ("B" "C1" "C1E" "C" "CE" "D1" "D1E" "D" "DE") ] .
:capacity       a owl:DatatypeProperty ; rdfs:range xsd:decimal .
:adrApproved    a owl:DatatypeProperty ; rdfs:domain :Vehicle ; rdfs:range xsd:boolean .
:unNumber       a owl:DatatypeProperty ; rdfs:domain :UNNumber ; rdfs:range xsd:string .

# ───────── Axioms ─────────
# A critical document must be a document (subsumption already stated).
# A non-startable order is one whose driver or vehicle has an expired critical document:
:NonStartableOrder owl:equivalentClass [
    a owl:Class ; owl:intersectionOf ( :Order
        [ a owl:Restriction ; owl:onProperty :hasDriver ;
          owl:someValuesFrom [ a owl:Restriction ; owl:onProperty :hasDocument ;
            owl:someValuesFrom [ a owl:Class ; owl:intersectionOf (
                :CriticalDocument
                [ a owl:Restriction ; owl:onProperty :documentState ; owl:hasValue "expired" ] ) ] ] ]
    )
] .
# (The vehicle-side restriction is analogous; both realize BR-D3.)

# Every document issued by exactly one party.
:Document rdfs:subClassOf
    [ a owl:Restriction ; owl:onProperty :issuedBy ;
      owl:qualifiedCardinality "1"^^xsd:nonNegativeInteger ; owl:onClass :Party ] .
```

### 10.7 Reasoning uses

- **Consistency**: detect a driver with no valid critical document referenced by a starting order.
- **Classification**: infer `NonStartableOrder` from an expired critical document — directly maps to the `button_start_order` guard.
- **Realization**: infer a vehicle is `ADRCompliant` iff `adrApproved=true` ∧ holds an `adr_vehicle` critical, valid document.

---

## 11. Glossary & references

**Turkish terms:** Sevkiyat, Yükleme/Boşaltma, Çekici, Dorse, Tonaj, Parsiyel, Full/Komple, Güzergah, Plaka, HGS/OGS, Vergi Dairesi/No, e-Fatura, e-Arşiv, e-İrsaliye, e-MM, K1/K2/K3, R1, SRC1-4, Psikoteknik, Muayene, ADR, UMTS, GİB, UDH, TOBB, Nilvera (Özel Entegratör).

**Normative references**
- Repo: `OCA/stock-logistics-transport`, branch `19.0` (AGPL-3).
- OCA `oca-addons-repo-template` (copier), `maintainer-tools`, `odoo-pre-commit`.
- GİB e-Fatura / e-İrsaliye (UBL-TR); UDH/TOBB carrier authorization & UMTS; ADR (UN/ECE).

**Internal**
- `docs/DEVELOPMENT_PLAN.md` — phased plan; MVP phases (`tms_document`, `l10n_tr_tms_document`, `tms_adr`) fully elaborated.
- Legacy `vsl_transport` (`volkantasci/vsl-tms-odoo`) — purpose reference only.
