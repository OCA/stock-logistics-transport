# Stay-on-Form Upload + Soft Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the driver/vehicle form open when documents are uploaded (refreshing the Documents tab in place) and add a per-row soft-delete (archive) action for documents.

**Architecture:** `create_document_from_attachment` stops returning a navigation action and returns `{"ids", "count"}`; the uploader widget then calls `this.props.record.load()` and shows a success notification. Documents are soft-deleted by overriding `unlink()` to set `active = False` (the field already exists), exposed via an `action_soft_delete()` button rendered per row in the `document_ids` inline list on the driver/vehicle forms. `active=False` records are auto-hidden by Odoo's default `active=True` search domain (holder tab, menu, trip-start guard).

**Tech Stack:** Odoo 19 Community, OCA conventions, `TransactionCase` tests, dockerized test runs against the `odoo_tests` database.

**Depends on:** `tms_document` 19.0.1.0.3 already installed (PR #231 content, incl. the `@api.model` RPC fix). **Branch:** `dev-integration` (current).

---

## Test-run command (used throughout)

The repo mounts to the running Odoo at `/mnt/oca-tms`. Run the `tms_document` test suite in the container:

```bash
PW=$(docker exec odoo-docker-web-1 cat /run/secrets/postgresql_password)
docker exec -i odoo-docker-web-1 odoo -d odoo_tests -u tms_document --test-enable \
  --stop-after-init --http-port=8091 --db_host db --db_port 5432 --db_user odoo \
  --db_password "$PW" --log-level=info 2>&1 | grep -E "Starting Test|stats:|error\(s\)|failed"
```

Expected at the end: `0 failed, 0 error(s) of N tests when loading database 'odoo_tests'` and `odoo.tests.stats: tms_document: N tests`.

---

## Task 1: `create_document_from_attachment` returns created ids

**Files:**
- Modify: `tms_document/models/tms_document.py` (lines 112–134)
- Modify: `tms_document/tests/test_tms_document.py` (three tests)

- [ ] **Step 1: Update the tests to expect the new return value**

In `tms_document/tests/test_tms_document.py`, replace `test_create_document_from_attachment`, `test_create_document_from_attachment_with_holder`, and `test_create_document_from_attachment_via_rpc` with:

```python
    def test_create_document_from_attachment(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "license.pdf", "datas": base64.b64encode(b"file-content")}
        )
        result = self.Doc.with_context(
            default_res_model="tms.driver", default_res_id=self.holder.id
        ).create_document_from_attachment(attachment.ids)
        self.assertEqual(result["count"], 1)
        docs = self.Doc.browse(result["ids"])
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs.name, "license.pdf")
        self.assertEqual(docs.datas, base64.b64encode(b"file-content"))

    def test_create_document_from_attachment_requires_holder(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "license.pdf", "datas": base64.b64encode(b"file-content")}
        )
        with self.assertRaises(UserError):
            self.Doc.create_document_from_attachment(attachment.ids)

    def test_create_document_from_attachment_with_holder(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "insurance.pdf", "datas": base64.b64encode(b"file-content")}
        )
        result = self.Doc.with_context(
            default_res_model="tms.driver", default_res_id=self.holder.id
        ).create_document_from_attachment(attachment.ids)
        docs = self.Doc.browse(result["ids"])
        self.assertEqual(docs.res_model, "tms.driver")
        self.assertEqual(docs.res_id, self.holder.id)

    def test_create_document_from_attachment_via_rpc(self):
        """The web client sends args=[attachment_ids] which call_kw treats as
        record ids (args[0]) unless the method is marked @api.model."""
        attachment = self.env["ir.attachment"].create(
            {"name": "via-rpc.pdf", "datas": base64.b64encode(b"file-content")}
        )
        result = call_kw(
            self.Doc,
            "create_document_from_attachment",
            [[attachment.id]],
            {
                "context": {
                    "default_res_model": "tms.driver",
                    "default_res_id": self.holder.id,
                }
            },
        )
        self.assertEqual(result["count"], 1)
        docs = self.Doc.browse(result["ids"])
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs.name, "via-rpc.pdf")
        self.assertEqual(docs.res_model, "tms.driver")
        self.assertEqual(docs.res_id, self.holder.id)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run the test-run command. Expected: `FAIL` on the three tests with something like
`KeyError: 'ids'` (the method still returns the action dict with `domain`, not `ids`).

- [ ] **Step 3: Change the method to return the created ids**

In `tms_document/models/tms_document.py`, replace the action-building block (currently lines 112–134, from `action = {` through `return action`) with:

```python
        return {"ids": docs.ids, "count": len(docs)}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run the test-run command. Expected: `0 failed, 0 error(s)` — all `tms_document` tests pass.

- [ ] **Step 5: Commit**

```bash
git add tms_document/models/tms_document.py tms_document/tests/test_tms_document.py
git commit -m "[IMP] tms_document: create_document_from_attachment returns created ids"
```

---

## Task 2: Uploader widget stays on the holder form

**Files:**
- Modify: `tms_document/static/src/document_uploader/document_uploader.esm.js`

- [ ] **Step 1: Edit the widget**

In `tms_document/static/src/document_uploader/document_uploader.esm.js`:

1. Add the translation import after the existing imports (line 5):

```js
import {_t} from "@web/core/l10n/translation";
```

2. Replace `onUploadComplete` (currently lines 41–54) with:

```js
    async onUploadComplete() {
        try {
            const attachmentIds = [...this.attachmentIdsToProcess];
            const {count} = await this.orm.call(
                "tms.document",
                "create_document_from_attachment",
                [attachmentIds],
                {context: this._getContext()}
            );
            await this.props.record.load();
            this.notification.add(
                _t("%(count)s document(s) uploaded", {count}),
                {type: "success"}
            );
        } finally {
            this.attachmentIdsToProcess = [];
        }
    }
```

`record.load()` reloads the holder record from the server, recomputing the
`document_ids` one2many so the newly uploaded documents appear in the tab; no
`doAction` navigation happens, so the user stays on the driver/vehicle form.

- [ ] **Step 2: Manual smoke check in the UI**

1. Ensure the web assets bundle is refreshed (clear the asset cache by creating and
   deleting a throwaway `ir.asset`, or restart the web container).
2. Open a saved *Driver* → *Documents* tab.
3. Upload a file → the driver form stays open, a *"1 document(s) uploaded"* success
   notification appears, and the new document shows in the list.

- [ ] **Step 3: Commit**

```bash
git add tms_document/static/src/document_uploader/document_uploader.esm.js
git commit -m "[IMP] tms_document: keep holder form open after document upload"
```

---

## Task 3: Soft delete on the model

**Files:**
- Modify: `tms_document/models/tms_document.py` (after `create_document_from_attachment`)
- Modify: `tms_document/tests/test_tms_document.py`

- [ ] **Step 1: Write the failing tests**

Append to `tms_document/tests/test_tms_document.py`:

```python
    def test_unlink_soft_deletes_document(self):
        doc = self._doc(fields.Date.to_date(date.today()) - timedelta(days=1))
        doc.critical = True
        doc.unlink()
        self.assertFalse(doc.active)
        self.assertNotIn(doc, self.holder.document_ids)

    def test_action_soft_delete_archives_and_unblocks_start(self):
        doc = self._doc(fields.Date.to_date(date.today()) - timedelta(days=1))
        doc.critical = True
        with self.assertRaises(UserError):
            self.order.button_start_order()
        doc.action_soft_delete()
        self.assertFalse(doc.active)
        self.assertNotIn(doc, self.holder.document_ids)
        self.order.button_start_order()
        self.assertTrue(self.order.start_trip)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run the test-run command. Expected: `FAIL` — `'tms.document' object has no attribute 'action_soft_delete'` and `doc.active` stays `True` after `unlink` (hard delete).

- [ ] **Step 3: Implement soft delete**

In `tms_document/models/tms_document.py`, after `create_document_from_attachment`, add:

```python
    def unlink(self):
        self.write({"active": False})
        return True

    def action_soft_delete(self):
        self.unlink()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run the test-run command. Expected: `0 failed, 0 error(s)`.

- [ ] **Step 5: Commit**

```bash
git add tms_document/models/tms_document.py tms_document/tests/test_tms_document.py
git commit -m "[IMP] tms_document: soft-delete documents via active flag"
```

---

## Task 4: Per-row Delete button on the holder Documents tab

**Files:**
- Modify: `tms_document/views/tms_driver_views.xml`
- Modify: `tms_document/views/fleet_vehicle_views.xml`
- Modify: `tms_document/__manifest__.py`

- [ ] **Step 1: Driver form — inline list with Delete button**

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
                    <div class="mb-2" invisible="not id">
                        <widget name="tms_document_uploader" />
                    </div>
                    <field name="document_ids">
                        <list>
                            <field name="name" />
                            <field name="doc_type" />
                            <field name="expiry_date" />
                            <field name="state" />
                            <button
                                name="action_soft_delete"
                                type="object"
                                string="Delete"
                                icon="fa-trash"
                                confirm="Delete this document?"
                            />
                        </list>
                    </field>
                </page>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 2: Vehicle form — inline list with Delete button**

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
                    <div class="mb-2" invisible="not id">
                        <widget name="tms_document_uploader" />
                    </div>
                    <field name="document_ids">
                        <list>
                            <field name="name" />
                            <field name="doc_type" />
                            <field name="expiry_date" />
                            <field name="state" />
                            <button
                                name="action_soft_delete"
                                type="object"
                                string="Delete"
                                icon="fa-trash"
                                confirm="Delete this document?"
                            />
                        </list>
                    </field>
                </page>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 3: Bump the module version**

In `tms_document/__manifest__.py`, change `"version": "19.0.1.0.3",` →
`"version": "19.0.1.0.4",`.

- [ ] **Step 4: Upgrade the module in the dev instance**

```bash
PW=$(docker exec odoo-docker-web-1 cat /run/secrets/postgresql_password)
docker exec -i odoo-docker-web-1 odoo -d odoo -u tms_document --stop-after-init \
  --http-port=8091 --db_host db --db_port 5432 --db_user odoo --db_password "$PW" \
  --log-level=warn 2>&1 | grep -iE "ERROR|tms_document" | tail -20
```

Expected: upgrade completes without view errors. Then restart the web container so the
running server picks up the new Python/views:

```bash
cd ~/dev/odoo-docker && ./restart.sh web
```

- [ ] **Step 5: Run the full test suite**

Run the test-run command. Expected: `0 failed, 0 error(s)`.

- [ ] **Step 6: Manual smoke check**

1. Open a saved *Driver* → *Documents* tab.
2. Upload a document (stays on the form; appears in the list).
3. Click the row trash icon → confirm dialog → the row disappears; the driver form
   stays open; the record's `active` is now `False` in the DB.
4. Repeat on a *Vehicle* form.

- [ ] **Step 7: Commit**

```bash
git add tms_document/views/tms_driver_views.xml tms_document/views/fleet_vehicle_views.xml \
  tms_document/__manifest__.py
git commit -m "[IMP] tms_document: per-row Delete button on holder Documents tab"
```

---

## Task 5: Final verification

**Files:** none (verification only).

- [ ] **Step 1: Lint the changed Python files**

```bash
cd ~/dev/odoo-tms && ruff format --check tms_document/models/tms_document.py \
  tms_document/tests/test_tms_document.py && \
  ruff check --config .ruff.toml tms_document/models/tms_document.py \
  tms_document/tests/test_tms_document.py 2>&1 | grep -v DTZ011
```

Expected: `2 files already formatted` and no findings other than the pre-existing
`DTZ011` warnings on untouched test lines.

- [ ] **Step 2: Full test run**

Run the test-run command once more. Expected: `0 failed, 0 error(s)`.

- [ ] **Step 3: Confirm soft-deleted docs don't resurface anywhere**

Query the dev DB — the archived document is `active = False` and absent from
`tms.driver.document_ids`:

```bash
docker exec odoo-docker-db-1 psql -U odoo -d odoo -c \
  "SELECT id, name, active FROM tms_document ORDER BY id DESC LIMIT 5;"
```

---

## Definition of done

- Uploading a document keeps the driver/vehicle form open, shows a success
  notification, and the new document appears in the *Documents* tab.
- `tms.document.unlink()` soft-deletes (`active = False`); `action_soft_delete()` is
  callable and a per-row Delete button on both holder forms triggers it with a
  confirmation.
- Soft-deleted documents are hidden everywhere (holder tab, menu, trip-start guard)
  with no restore UI.
- `create_document_from_attachment` returns `{"ids", "count"}`; all tests pass; module
  version bumped to `19.0.1.0.4`; ruff clean.

---

## Self-review

**Spec coverage:**

- §Solution 1 (stay on form: server returns ids, widget `record.load()` + notification)
  → Tasks 1–2. ✅
- §Solution 2 (soft delete: `unlink` override, `action_soft_delete`, inline list button
  on both forms, trip-start unaffected) → Tasks 3–4. ✅
- §Testing (updated upload tests, soft-delete test incl. trip-start unblock; version
  bump) → Tasks 1, 3, 4. ✅
- §Out of scope (no restore UI, no menu changes) → plan touches none of those. ✅

**Placeholder scan:** no TBD/TODO; all code and commands inline.

**Type consistency:** `create_document_from_attachment` → `{"ids", "count"}` used
identically in Task 1 tests and Task 2 widget; `unlink` / `action_soft_delete` /
`active` / `document_ids` used consistently across Tasks 3–4. ✅
