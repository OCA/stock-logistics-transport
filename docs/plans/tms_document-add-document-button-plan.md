# Add Document Button on Holder Forms Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or superpowers:executing-plans
> to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add an "Add Document" button inside the _Documents_ page of the driver and
vehicle forms that opens a `tms.document` dialog pre-filled with the holder.

**Architecture:** A new `ir.actions.act_window` (`action_tms_document_new`,
`view_mode="form"`, `target="new"`) is opened by a small `action_add_document()` method
added to both `tms.driver` and `fleet.vehicle`. The method builds the action via
`_for_xml_id()` and injects `default_res_model` / `default_res_id` from `self`,
guaranteeing the holder is always pre-filled. A button in the existing _Documents_ page
(hidden until the record is saved) triggers it. Tests verify the returned action context
for both holder models.

**Tech Stack:** Odoo 19 Community, OCA conventions, `TransactionCase` tests, dockerized
test runs against the `odoo` database.

**Depends on:** `tms_document` module already installed (PR #231 content). **Branch:**
`dev-integration` (current).

---

## Test-run command (used throughout)

The repo mounts to the running Odoo at `/mnt/oca-tms`. Run tests in the container:

```bash
docker compose -f ~/dev/odoo-docker/docker-compose.yml exec web odoo \
  --test-enable -d odoo -i tms_document --test-tags=/tms_document \
  --stop-after-init --no-http 2>&1 | grep -E "FAIL|ERROR|passed|failed"
```

Expected at the end: `tms_document` tests pass (13 existing + 2 new).

---

## Task 1: Model method `action_add_document()`

**Files:**

- Modify: `tms_document/models/tms_driver.py`
- Modify: `tms_document/models/fleet_vehicle.py`
- Test: `tms_document/tests/test_tms_document.py`

- [x] **Step 1: Write the failing tests**

Append to `tms_document/tests/test_tms_document.py`:

```python
    def test_action_add_document_driver(self):
        action = self.holder.action_add_document()
        self.assertEqual(action["res_model"], "tms.document")
        self.assertEqual(
            action["context"],
            {"default_res_model": "tms.driver", "default_res_id": self.holder.id},
        )

    def test_action_add_document_vehicle(self):
        vehicle = self._make_vehicle()
        action = vehicle.action_add_document()
        self.assertEqual(action["res_model"], "tms.document")
        self.assertEqual(
            action["context"],
            {
                "default_res_model": "fleet.vehicle",
                "default_res_id": vehicle.id,
            },
        )
```

- [x] **Step 2: Run tests to verify they fail**

Run the test-run command above. Expected: FAIL —
`'tms.driver' object has no attribute 'action_add_document'`.

- [x] **Step 3: Implement the method on `tms.driver`**

Add to `tms_document/models/tms_driver.py`:

```python
    def action_add_document(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "tms_document.action_tms_document_new"
        )
        action["context"] = {
            "default_res_model": "tms.driver",
            "default_res_id": self.id,
        }
        return action
```

- [x] **Step 4: Implement the method on `fleet.vehicle`**

Add to `tms_document/models/fleet_vehicle.py`:

```python
    def action_add_document(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "tms_document.action_tms_document_new"
        )
        action["context"] = {
            "default_res_model": "fleet.vehicle",
            "default_res_id": self.id,
        }
        return action
```

Note: the xmlid `action_tms_document_new` does not exist yet (Task 2). Tests will fail
until Task 2 lands — expected. If you want a green run between tasks, comment the two
new tests out, run, then restore.

- [x] **Step 5: Run tests**

Run the test-run command. Expected: the two new tests still FAIL with
`External ID not found: tms_document.action_tms_document_new` — this is the Task-2
dependency.

- [x] **Step 6: Commit**

```bash
git add tms_document/models/tms_driver.py tms_document/models/fleet_vehicle.py \
  tms_document/tests/test_tms_document.py
git commit -m "[ADD] tms_document: action_add_document on driver and vehicle"
```

---

## Task 2: `action_tms_document_new` action + view buttons

**Files:**

- Modify: `tms_document/views/tms_document_views.xml` (add action)
- Modify: `tms_document/views/tms_driver_views.xml` (add button)
- Modify: `tms_document/views/fleet_vehicle_views.xml` (add button)
- Modify: `tms_document/__manifest__.py` (bump version)

- [x] **Step 1: Add the new action**

In `tms_document/views/tms_document_views.xml`, after the existing `action_tms_document`
record, add:

```xml
<record id="action_tms_document_new" model="ir.actions.act_window">
  <field name="name">New Document</field>
  <field name="res_model">tms.document</field>
  <field name="view_mode">form</field>
  <field name="target">new</field>
</record>
```

- [x] **Step 2: Add the button to the driver form**

Replace the whole `tms_document/views/tms_driver_views.xml` file with:

```xml
<?xml version="1.0" encoding="utf-8" ?>
<odoo>
  <record id="view_tms_driver_documents" model="ir.ui.view">
    <field name="name">tms.driver.documents</field>
    <field name="model">tms.driver</field>
    <field name="inherit_id" ref="tms.view_tms_driver_form_inherit" />
    <field name="arch" type="xml">
      <xpath expr="//form//notebook" position="inside">
        <page string="Documents">
          <button
            name="action_add_document"
            type="object"
            string="Add Document"
            class="btn-primary"
            icon="fa-upload"
            invisible="not id"
          />
          <field name="document_ids" />
        </page>
      </xpath>
    </field>
  </record>
</odoo>
```

- [x] **Step 3: Add the button to the vehicle form**

Replace the whole `tms_document/views/fleet_vehicle_views.xml` file with:

```xml
<?xml version="1.0" encoding="utf-8" ?>
<odoo>
  <record id="view_fleet_vehicle_documents" model="ir.ui.view">
    <field name="name">fleet.vehicle.documents</field>
    <field name="model">fleet.vehicle</field>
    <field name="inherit_id" ref="tms.fleet_vehicle_inherit_view_form" />
    <field name="arch" type="xml">
      <xpath expr="//form//notebook" position="inside">
        <page string="Documents">
          <button
            name="action_add_document"
            type="object"
            string="Add Document"
            class="btn-primary"
            icon="fa-upload"
            invisible="not id"
          />
          <field name="document_ids" />
        </page>
      </xpath>
    </field>
  </record>
</odoo>
```

- [x] **Step 4: Bump module version**

In `tms_document/__manifest__.py`, change: `"version": "19.0.1.0.0",` →
`"version": "19.0.1.0.1",`

- [x] **Step 5: Upgrade the module in the running instance**

```bash
docker compose -f ~/dev/odoo-docker/docker-compose.yml exec web odoo \
  -d odoo -u tms_document --stop-after-init --no-http 2>&1 | grep -E "ERROR|tms_document"
```

Expected: upgrade completes without view/action errors.

- [x] **Step 6: Run the full test suite**

Run the test-run command. Expected: all 15 `tms_document` tests pass.

- [x] **Step 7: Commit**

```bash
git add tms_document/views/ tms_document/__manifest__.py
git commit -m "[ADD] tms_document: Add Document button on driver and vehicle forms"
```

---

## Task 3: Pre-commit + final verification

**Files:** none (verification only).

- [x] **Step 1: Run pre-commit on the module**

```bash
cd ~/dev/odoo-tms && pre-commit run --files tms_document/** 2>/dev/null \
  || pre-commit run --all-files
```

Expected: clean (no `black`, `isort`, `oca-checks`, or `ruff` findings).

- [x] **Step 2: Manual smoke check in the UI**

1. Open _Drivers_ → _Create_ → save the driver.
2. Open the _Documents_ tab → confirm an **Add Document** button appears above the list.
3. Click it → a `tms.document` dialog opens with the holder already set to the driver.
4. Repeat for _Vehicles_ (a saved vehicle's _Documents_ tab).
5. Confirm the button is hidden while the driver/vehicle form is unsaved.

- [x] **Step 3: Final test run**

Run the test-run command once more. Expected: all tests pass.

---

## Definition of done

- `tms.driver.action_add_document()` and `fleet.vehicle.action_add_document()` return an
  action with `res_model="tms.document"` and correct
  `default_res_model`/`default_res_id` context (2 new tests).
- "Add Document" button appears inside the _Documents_ page of both the driver and
  vehicle forms, hidden when the holder is unsaved, and opens the document form as a
  dialog pre-filled with the holder.
- `tms_document` version bumped to `19.0.1.0.1`; module upgrades cleanly; all tests
  pass; `pre-commit` clean.

---

## Self-review

**Spec coverage:**

- §Architecture (action, method, view) → Tasks 1–2. ✅
- §Testing (2 new tests, driver + vehicle) → Task 1 Steps 1–2. ✅
- §Out of scope (no model/security/guard changes) → plan touches only models' new
  method, views, action, version. ✅

**Placeholder scan:** no TBD/TODO; all code and commands inline.

**Type consistency:** `action_add_document`, `action_tms_document_new`,
`default_res_model`, `default_res_id` used identically across tasks. ✅
