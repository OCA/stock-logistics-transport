# `tms_document` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox
> (`- [ ]`) syntax for tracking.

**Goal:** Add `tms_document`, a generic, polymorphic, expiry-tracked document framework
to the OCA `stock-logistics-transport` `19.0` repo, and wire it into the existing
`tms.order.button_start_order` so that expired _critical_ documents block trip start.

**Architecture:** A single `tms.document` model holds typed documents against any holder
via the standard Odoo generic-relation pattern (`res_model` + `res_id`, like
`ir.attachment`). Validity (`valid / expiring / expired`) is a **non-stored** compute
(deliberately not stored, so it always reflects _today_ — fixing the legacy store=True
bug). Drivers and vehicles gain a computed One2many of their documents.
`button_start_order` is extended via `super()` with a pre-check that searches expired
critical documents by `expiry_date` (searchable).

**Tech Stack:** Odoo 19 Community (Python 3.12), OCA conventions, `TransactionCase`
tests, copier `readme/` fragments.

**Depends on:** `tms`. **Branch:** `19.0-add-tms_document` (already created).

---

## Conventions (verified against the existing core)

- **Groups** use Odoo 19 `res.groups.privilege` + `res.groups.privilege_id` (NOT
  `ir.module.category`). Existing: `tms.group_tms_user`, `tms.group_tms_admin`.
- **Access CSV** format:
  `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink`;
  `user`=read-only, `admin`=full.
- **Tests** in `tests/test_*.py`, registered in `tests/__init__.py`, class
  `TransactionCase` with `@classmethod setUpClass`.
- **License header** on every Python file:
  ```python
  # Copyright (C) 2026 VSL
  # License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
  ```
- **`button_start_order`** lives in `tms/models/tms_order.py`; we extend, do not
  replace.

---

## File structure

```
tms_document/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── tms_document.py          # the polymorphic document model + expiry compute
│   ├── tms_driver.py            # inherit: computed document_ids O2M
│   ├── fleet_vehicle.py         # inherit: computed document_ids O2M
│   └── tms_order.py             # inherit: _tms_document_check_critical + button_start_order
├── data/
│   └── ir_config_parameter.xml  # tms.document.expiry_horizon_days = 30
├── security/
│   ├── res_groups.xml           # privilege + group_tms_document
│   └── ir.model.access.csv
├── views/
│   ├── tms_document_views.xml   # list, form, search, action
│   ├── tms_driver_views.xml     # inherit: documents page
│   ├── fleet_vehicle_views.xml  # inherit: documents page
│   └── menu.xml
├── readme/
│   ├── DESCRIPTION.md
│   ├── USAGE.md
│   ├── CONFIGURE.md
│   ├── CREDITS.md
│   ├── CONTRIBUTORS.md
│   └── MAINTAINERS.md
├── static/description/icon.png  # placeholder 96x96
└── tests/
    ├── __init__.py
    └── test_tms_document.py
```

---

## Task 1: Module skeleton (installs cleanly)

**Files:** Create `tms_document/__init__.py`, `tms_document/__manifest__.py`,
`tms_document/models/__init__.py`.

- [ ] **Step 1: `tms_document/__init__.py`**

```python
from . import models
```

- [ ] **Step 2: `tms_document/models/__init__.py`**

```python
from . import tms_document
from . import tms_driver
from . import fleet_vehicle
from . import tms_order
```

- [ ] **Step 3: `tms_document/__manifest__.py`**

```python
# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS Document",
    "summary": "Generic expiry-tracked document framework for TMS",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "VSL, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "maintainers": ["volkantasci"],
    "development_status": "Beta",
    "installable": True,
    "application": False,
    "depends": ["tms"],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "views/tms_document_views.xml",
        "views/tms_driver_views.xml",
        "views/fleet_vehicle_views.xml",
        "views/menu.xml",
    ],
}
```

(The `models/*.py` imports in Step 2 will fail until Tasks 3–6 land; temporarily comment
out `tms_driver`, `fleet_vehicle`, `tms_order` imports for the Task-1 install check,
then restore.)

- [ ] **Step 4: Install check**

```bash
docker compose -f ~/dev/odoo/docker-compose.yml stop web
docker compose -f ~/dev/odoo/docker-compose.yml run --rm web odoo \
  -d odoo -i tms_document --stop-after-init
docker compose -f ~/dev/odoo/docker-compose.yml up -d web
```

Expected: module installs (no models yet beyond placeholder).

- [ ] **Step 5: Commit**

```bash
git add tms_document
git commit -m "[ADD] tms_document: module skeleton"
```

---

## Task 2: Security group + access rights

**Files:** Create `tms_document/security/res_groups.xml`,
`tms_document/security/ir.model.access.csv`. Test: `tms_document/tests/__init__.py`,
`tms_document/tests/test_security.py`.

- [ ] **Step 1: Failing test** — `tests/test_security.py`

```python
from odoo.tests.common import TransactionCase


class TestSecurity(TransactionCase):
    def test_group_exists(self):
        self.env.ref("tms_document.group_tms_document", raise_if_not_found=True)
```

- [ ] **Step 2: `tests/__init__.py`**

```python
from . import test_security
```

- [ ] **Step 3: Run — expect FAIL**

```bash
docker compose -f ~/dev/odoo/docker-compose.yml stop web
docker compose -f ~/dev/odoo/docker-compose.yml run --rm web odoo \
  --test-enable -d odoo -i tms_document --test-tags=/tms_document:TestSecurity --stop-after-init
```

Expected: FAIL — External ID `tms_document.group_tms_document` not found.

- [ ] **Step 4: Implement** — `security/res_groups.xml`

```xml
<?xml version="1.0" encoding="utf-8" ?>
<odoo>
  <record id="privilege_tms_document" model="res.groups.privilege">
    <field name="name">Manage TMS Documents</field>
    <field name="category_id" ref="base.module_category_hidden" />
  </record>
  <record id="group_tms_document" model="res.groups">
    <field name="name">Manage TMS Documents</field>
    <field name="privilege_id" ref="privilege_tms_document" />
    <field name="implied_ids" eval="[(4, ref('tms.group_tms_user'))]" />
  </record>
</odoo>
```

- [ ] **Step 5: `security/ir.model.access.csv`** (one row; will grow as models land)

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_tms_document_user,tms.document.user,tms_document.model_tms_document,tms.group_tms_user,1,0,0,0
access_tms_document_admin,tms.document.admin,tms_document.model_tms_document,tms.group_tms_admin,1,1,1,1
```

- [ ] **Step 6: Run — PASS.** Commit.

```bash
git add tms_document
git commit -m "[ADD] tms_document: security group and access"
```

---

## Task 3: `tms.document` model with expiry compute (TDD)

**Files:** Create `tms_document/models/tms_document.py`. Test:
`tests/test_tms_document.py`.

- [ ] **Step 1: Failing test** — `tests/test_tms_document.py`

```python
from datetime import date, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestTmsDocument(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.holder = cls.env["tms.driver"].create({"name": "Doc Holder"})
        cls.Doc = cls.env["tms.document"]

    def _doc(self, expiry):
        return self.Doc.create({
            "res_model": "tms.driver",
            "res_id": self.holder.id,
            "doc_type": "license",
            "name": "LIC-1",
            "expiry_date": expiry,
        })

    def test_state_valid(self):
        d = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.assertEqual(d.state, "valid")

    def test_state_expired(self):
        d = self._doc(fields.Date.to_date(date.today()) - timedelta(days=1))
        self.assertEqual(d.state, "expired")

    def test_state_expiring_within_horizon(self):
        d = self._doc(fields.Date.to_date(date.today()) + timedelta(days=5))
        self.assertEqual(d.state, "expiring")
```

- [ ] **Step 2: Register test** — `tests/__init__.py`

```python
from . import test_security
from . import test_tms_document
```

- [ ] **Step 3: Run — FAIL** (`tms.document` model missing).

- [ ] **Step 4: Implement** — `models/tms_document.py`

```python
# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class TmsDocument(models.Model):
    _name = "tms.document"
    _description = "TMS Document"
    _order = "expiry_date asc nulls last"
    _rec_name = "name"

    res_model = fields.Char(string="Holder Model", required=True, index=True)
    res_id = fields.Integer(string="Holder ID", required=True, index=True)
    res_ref = fields.Reference(
        selection="_selection_res_model", compute="_compute_res_ref",
        string="Holder", readonly=False, store=False,
    )

    doc_type = fields.Selection(
        selection="_selection_doc_type", string="Type", required=True,
    )
    name = fields.Char(string="Reference", required=True)
    issue_date = fields.Date()
    expiry_date = fields.Date(index=True)
    state = fields.Selection(
        [("valid", "Valid"), ("expiring", "Expiring"), ("expired", "Expired")],
        compute="_compute_state", string="State", store=False,
    )
    critical = fields.Boolean(
        default=False,
        help="If checked, an expired document blocks trip start on its holder.",
    )
    datas = fields.Binary(string="File", attachment=True)
    notes = fields.Text()
    company_id = fields.Many2one(
        "res.company", string="Company",
        default=lambda self: self.env.company, required=True,
    )
    active = fields.Boolean(default=True)

    def _selection_res_model(self):
        return [("tms.driver", "Driver"), ("fleet.vehicle", "Vehicle")]

    def _selection_doc_type(self):
        # Extensible: l10n_tr_tms_document adds K/SRC/etc.; tms_adr adds adr_*.
        return [
            ("license", "Driving License"),
            ("insurance", "Insurance"),
            ("inspection", "Vehicle Inspection"),
            ("other", "Other"),
        ]

    @api.depends("res_model", "res_id")
    def _compute_res_ref(self):
        for rec in self:
            if rec.res_model and rec.res_id and rec.res_model in self.env:
                rec.res_ref = f"{rec.res_model},{rec.res_id}"
            else:
                rec.res_ref = False

    @api.depends("expiry_date")
    @api.depends_context("uid")  # recompute when date context changes
    def _compute_state(self):
        today = fields.Date.context_today(self)
        horizon = self._get_expiry_horizon_days()
        for rec in self:
            if not rec.expiry_date:
                rec.state = "valid"
            elif rec.expiry_date < today:
                rec.state = "expired"
            elif rec.expiry_date < today + timedelta_horizon(horizon):
                rec.state = "expiring"
            else:
                rec.state = "valid"
```

(`timedelta_horizon(n)` and `_get_expiry_horizon_days()` are defined in Task 4; for now
inline a helper so tests pass: read `ir.config_parameter`
`tms.document.expiry_horizon_days` default 30, and `from datetime import timedelta`.)

> **Why `store=False`:** the legacy module stored this compute, which never recomputes
> as days pass — so a document that "expires tonight" is wrongly shown valid forever.
> Non-stored guarantees correctness. Searches use the searchable `expiry_date` instead.

- [ ] **Step 5: Run — PASS.** Commit.

```bash
git add tms_document
git commit -m "[ADD] tms_document: document model with non-stored validity compute"
```

---

## Task 4: Configurable expiry horizon

**Files:** Add `tms_document/data/ir_config_parameter.xml`; finish the horizon helper in
`tms_document.py`.

- [ ] **Step 1: Failing test** — append to `test_tms_document.py`

```python
    def test_horizon_respected(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "tms.document.expiry_horizon_days", 60
        )
        d = self._doc(fields.Date.to_date(date.today()) + timedelta(days=40))
        self.assertEqual(d.state, "expiring")  # within 60-day horizon
```

- [ ] **Step 2: Run — FAIL** (helper returns default 30 → 40 days is "valid").

- [ ] **Step 3: Implement** — finalize `models/tms_document.py` helpers:

```python
    from datetime import timedelta  # top of file

    def _get_expiry_horizon_days(self):
        return int(
            self.env["ir.config_parameter"].sudo().get_param(
                "tms.document.expiry_horizon_days", "30"
            )
        )
```

and in `_compute_state` replace `timedelta_horizon(horizon)` with
`timedelta(days=horizon)`.

- [ ] **Step 4: `data/ir_config_parameter.xml`**

```xml
<?xml version="1.0" encoding="utf-8" ?>
<odoo noupdate="1">
  <record id="default_expiry_horizon" model="ir.config_parameter">
    <field name="key">tms.document.expiry_horizon_days</field>
    <field name="value">30</field>
  </record>
</odoo>
```

- [ ] **Step 5: Run — PASS.** Commit.

```bash
git add tms_document
git commit -m "[IMP] tms_document: configurable expiry horizon"
```

---

## Task 5: Holder One2many + navigation

**Files:** Create `tms_document/models/tms_driver.py`,
`tms_document/models/fleet_vehicle.py`. Test additions.

- [ ] **Step 1: Failing test** — append to `test_tms_document.py`

```python
    def test_driver_documents_o2m(self):
        self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.assertEqual(len(self.holder.document_ids), 1)
        self.assertEqual(self.holder.document_ids.state, "valid")
```

- [ ] **Step 2: Run — FAIL** (`tms.driver` has no `document_ids`).

- [ ] **Step 3: Implement** — `models/tms_driver.py`

```python
# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class TmsDriver(models.Model):
    _inherit = "tms.driver"

    document_ids = fields.One2many(
        "tms.document", "res_id", string="Documents", compute="_compute_document_ids"
    )

    @api.depends("id")
    def _compute_document_ids(self):
        Doc = self.env["tms.document"]
        for rec in self:
            rec.document_ids = Doc.search(
                [("res_model", "=", "tms.driver"), ("res_id", "=", rec.id)]
            )
```

`models/fleet_vehicle.py` — identical pattern with `"fleet.vehicle"`:

```python
# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    document_ids = fields.One2many(
        "tms.document", "res_id", string="Documents", compute="_compute_document_ids"
    )

    @api.depends("id")
    def _compute_document_ids(self):
        Doc = self.env["tms.document"]
        for rec in self:
            rec.document_ids = Doc.search(
                [("res_model", "=", "fleet.vehicle"), ("res_id", "=", rec.id)]
            )
```

Restore the imports in `models/__init__.py` (all four now exist).

- [ ] **Step 4: Run — PASS.** Commit.

```bash
git add tms_document
git commit -m "[ADD] tms_document: computed document_ids O2M on driver and vehicle"
```

---

## Task 6: Critical-document guard on `button_start_order` (TDD)

**Files:** Create `tms_document/models/tms_order.py`. Test additions.

- [ ] **Step 1: Failing test** — append to `test_tms_document.py`

```python
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.holder = cls.env["tms.driver"].create({"name": "Doc Holder"})
        cls.Doc = cls.env["tms.document"]
        # an order with the holder as driver
        cls.stage = cls.env["tms.stage"].create(
            {"name": "S", "stage_type": "order", "sequence": 1}
        )
        cls.order = cls.env["tms.order"].create({"driver_id": cls.holder.id})

    def test_start_blocked_when_critical_expired(self):
        self._doc(fields.Date.to_date(date.today()) - timedelta(days=1))
        self.holder.document_ids.write({"critical": True})
        with self.assertRaises(UserError):
            self.order.button_start_order()

    def test_start_ok_when_no_critical_expired(self):
        # critical but still valid
        self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.holder.document_ids.write({"critical": True})
        self.order.button_start_order()
        self.assertTrue(self.order.start_trip)
```

Add `from odoo.exceptions import UserError` to the test imports.

- [ ] **Step 2: Run — FAIL** (no `_tms_document_check_critical`; `button_start_order`
      not extended).

- [ ] **Step 3: Implement** — `models/tms_order.py`

```python
# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models
from odoo.exceptions import UserError


class TmsOrder(models.Model):
    _inherit = "tms.order"

    def button_start_order(self):
        # Run our critical-document check BEFORE the core mutates date_start.
        self._tms_document_check_critical()
        return super().button_start_order()

    def _tms_document_check_critical(self):
        today = fields.Date.context_today(self)
        holders = [(m, r) for m, r in (
            ("tms.driver", self.driver_id), ("fleet.vehicle", self.vehicle_id),
        ) if r]
        for model, holder in holders:
            expired = self.env["tms.document"].search([
                ("res_model", "=", model),
                ("res_id", "=", holder.id),
                ("critical", "=", True),
                ("expiry_date", "<", today),
            ])
            if expired:
                names = ", ".join(f"{d.name} ({d.doc_type})" for d in expired)
                raise UserError(
                    self.env._(
                        "Cannot start the trip: %(holder)s has expired critical "
                        "document(s): %(docs)s",
                        holder=holder.display_name, docs=names,
                    )
                )
```

Add `from odoo import fields` import.

- [ ] **Step 4: Run — PASS** for both guard tests.

  > Note: `button_start_order` in the core also checks vehicle insurance / driver
  > license inline; with our `tms_document` installed those inline checks still run in
  > `super()`. Keep both — our check is additive.

- [ ] **Step 5: Commit.**

```bash
git add tms_document
git commit -m "[ADD] tms_document: block trip start on expired critical documents"
```

---

## Task 7: Views + menu

**Files:** Create `views/tms_document_views.xml`, `views/tms_driver_views.xml`,
`views/fleet_vehicle_views.xml`, `views/menu.xml`. Add `static/description/icon.png`.

- [ ] **Step 1: `views/tms_document_views.xml`** — `<list>` (Odoo 19, not `<tree>`), no
      `attrs`/`states`. Fields: `name`, `doc_type`, `res_ref`, `issue_date`,
      `expiry_date`, `state` (badge), `critical`. Form with the same + `datas` (widget
      `binary`) + `notes`. Search view with filters: _Expired_, _Expiring_, _Critical_.

- [ ] **Step 2: `views/tms_driver_views.xml`** — inherit the driver form
      (`tms.tms_driver_form` or the core's form id; verify via
      `grep -r "tms.driver" tms/views/`), add a notebook page "Documents" with
      `<field name="document_ids">` and an inline `<list>`/`<form>` (the O2M is
      computed; users create documents via the dedicated menu or by setting
      res_model/res_id).

  > Verify the exact parent view xmlid before inheriting:
  > `rg "<record.*tms.driver.*form" ~/dev/odoo-tms/tms/views/`. If the core uses an
  > in-form notebook, add a page there.

- [ ] **Step 3: `views/fleet_vehicle_views.xml`** — same pattern for `fleet.vehicle`
      form.

- [ ] **Step 4: `views/menu.xml`** — under the existing TMS menu (`tms.menu_tms_root` —
      verify with `rg "menu_tms" ~/dev/odoo-tms/tms/views/menu.xml`), add a "Documents"
      submenu pointing to the action.

- [ ] **Step 5: Smoke test** — upgrade, open Documents menu, create a document linked to
      a driver; set expiry in the past + critical → start that driver's order → expect
      `UserError`.

- [ ] **Step 6: Commit.**

```bash
git add tms_document
git commit -m "[ADD] tms_document: views, holder inheritance and menu"
```

---

## Task 8: readme fragments, icon, i18n export, pre-commit

**Files:** `readme/*.md`, `static/description/icon.png`, `i18n/tms_document.pot`.

- [ ] **Step 1: `readme/DESCRIPTION.md`**

```markdown
Generic, expiry-tracked document framework for the TMS.

Attach typed documents (license, insurance, inspection, …) to any TMS resource (drivers,
vehicles). Document validity (valid / expiring / expired) is computed from the expiry
date against a configurable horizon.

A document can be flagged _critical_: an expired critical document on a trip's driver or
vehicle blocks starting that trip.
```

- [ ] **Step 2:** Write `readme/USAGE.md`, `readme/CONFIGURE.md` (the horizon param),
      `readme/CREDITS.md` (VSL, OCA), `readme/CONTRIBUTORS.md` (`Volkan Taşçı`),
      `readme/MAINTAINERS.md` (`volkantasci`). Place a 96×96
      `static/description/icon.png`.

- [ ] **Step 3: Export translation template**

```bash
docker compose -f ~/dev/odoo/docker-compose.yml exec web odoo \
  -d odoo --i18n-export=/mnt/extra-addons/tms_document/i18n/tms_document.pot \
  --modules=tms_document --stop-after-init
```

- [ ] **Step 4: Pre-commit**

```bash
pre-commit run --files tms_document/** 2>/dev/null || pre-commit run --all-files
```

Expected: clean (fix any `black`/`isort`/`oca-checks` findings).

- [ ] **Step 5: Commit.**

```bash
git add tms_document
git commit -m "[ADD] tms_document: readme fragments, icon and translation template"
```

---

## Definition of done

- `tms_document` installs on top of `tms`; all tests in `tms_document` pass
  (`--test-tags=/tms_document`).
- Documents attach to drivers and vehicles; `state` correctly reflects today.
- An expired _critical_ document on a trip's driver or vehicle blocks
  `button_start_order` (BR-D3), naming the offending document.
- Horizon is configurable via `tms.document.expiry_horizon_days`.
- `pre-commit` clean; `README.md` generates from `readme/`.

---

## Self-review

**Spec coverage (vs `docs/DESIGN.md`):**

- §4.2 `tms_document` model (polymorphic holder, expiry, critical) → Tasks 3–6. ✅
- §5.2 document FSM (valid/expiring/expired) → Task 3 (non-stored compute). ✅
- §6 BR-D1/D2/D3 → Tasks 3, 4, 6. ✅
- §3.2 R1, R2, R3 → Tasks 3, 3+4, 6. ✅

**Placeholder scan:** no TBD/TODO in elaborated steps. View xmlids require a `grep`
verification (Task 7 step 2/4) because the exact core view IDs must be confirmed at
implementation time — this is a verification step, not a placeholder.

**Name consistency:** `tms.document`, fields
`res_model`/`res_id`/`res_ref`/`doc_type`/`expiry_date`/`state`/`critical`, group
`tms_document.group_tms_document`, method `_tms_document_check_critical` — identical
across tasks and aligned with `docs/DESIGN.md`. ✅

---

## Execution handoff

Plan saved to `docs/plans/tms_document.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task with review
   between tasks (REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`).
2. **Inline Execution** — execute tasks in this session with checkpoints (REQUIRED
   SUB-SKILL: `superpowers:executing-plans`).
