# `tms_document`: Add Document Button on Holder Forms — Design

**Date:** 2026-08-09

**Goal:** Let users create/upload a `tms.document` directly from the holder form
(driver and vehicle), instead of going through the *Documents* menu.

**Problem:** `tms.driver.document_ids` and `fleet.vehicle.document_ids` are computed
One2many fields **without an inverse**, so Odoo renders them read-only. There is no
"Add" affordance on the holder form; documents can only be created from the
*Documents* menu. See `USAGE.md`:

> Documents are always created from the *Documents* menu — there is no button on
> the driver or vehicle form that creates or pre-fills them.

## Solution

Add an **"Add Document"** button inside the existing *Documents* page of both the
driver and vehicle form. Clicking it opens the `tms.document` form as a dialog
(`target="new"`) with `res_model` / `res_id` pre-filled from the holder, so the user
only fills in type, reference, dates and (optionally) the file.

## Architecture

1. **New action** `action_tms_document_new` (`ir.actions.act_window`):
   `res_model="tms.document"`, `view_mode="form"`, `target="new"`.

2. **Model method** `action_add_document()` on `tms.driver` and `fleet.vehicle`:
   ```python
   def action_add_document(self):
       self.ensure_one()
       action = self.env["ir.actions.act_window"]._for_xml_id(
           "tms_document.action_tms_document_new"
       )
       action["context"] = {"default_res_model": self._name, "default_res_id": self.id}
       return action
   ```
   A method (rather than a static action with context) guarantees the holder is
   always correct regardless of caller context.

3. **View changes** — inside the existing `Documents` page of
   `tms_driver_views.xml` and `fleet_vehicle_views.xml`:
   ```xml
   <page string="Documents">
       <button name="action_add_document" type="object"
               string="Add Document" class="btn-primary" icon="fa-upload"
               invisible="not id"/>
       <field name="document_ids" />
   </page>
   ```
   - `invisible="not id"`: button hidden until the holder is saved (a document needs
     a `res_id`).
   - No smart button / `oe_stat_button` — the user explicitly wants the button inside
     the page, not in the form header.

## Testing

New test in `tests/test_tms_document.py` verifying `action_add_document()` returns
an action whose context carries the correct `default_res_model` / `default_res_id`,
for both a driver and a vehicle holder.

## Out of scope

- No changes to `tms.document` model, security, or trip-start guard.
- Documents page remains a read-only summary list; creation goes through the dialog.
