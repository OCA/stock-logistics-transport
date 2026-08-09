# `tms_document`: Stay-on-Form Upload + Soft Delete — Design

**Date:** 2026-08-09

**Goal:** Improve the holder-form document UX in two ways:

1. Uploading documents from the driver/vehicle *Documents* tab must **keep the user on
   the holder form** (today it navigates away to the generated `tms.document` list /
   form) and show the newly uploaded documents immediately in the tab.
2. Add a per-row **Delete** action on the *Documents* tab that **soft-deletes**
   (`active = False`, archive-style) — no hard deletion, no restore UI.

## Problem

- `create_document_from_attachment` returns an `ir.actions.act_window` navigation
  action; the uploader widget calls `doAction(action)`, leaving the driver/vehicle
  form.
- `tms.document` has no delete affordance on the holder form, and deletion today would
  hard-remove the record (and its `datas` attachment).

## Solution

### 1. Stay on the holder form after upload

- **Model** — `create_document_from_attachment` stops returning a navigation action.
  It returns the created document ids instead:
  ```python
  return {"ids": docs.ids, "count": len(docs)}
  ```
- **Widget** (`document_uploader.esm.js`) — in `onUploadComplete`, replace
  `doAction(action)` with:
  ```js
  const { count } = await this.orm.call(...);
  await this.props.record.load();          // refresh document_ids on the holder form
  this.notification.add(...`${count} document(s) uploaded`...);
  ```
  `record.load()` re-reads the holder record from the server, so the computed
  `document_ids` o2m recomputes and the new documents appear in the tab. The user
  stays on the driver/vehicle form.

### 2. Soft delete

- **Model** (`tms_document.py`):
  - Override `unlink()` to soft-delete instead of hard-delete:
    ```python
    def unlink(self):
        self.write({"active": False})
        return True
    ```
    `active` already exists on the model; the default `active=True` search domain then
    hides archived documents everywhere (holder tab, Documents menu, trip-start check).
  - Add a button method:
    ```python
    def action_soft_delete(self):
        self.unlink()
    ```
    Returning `None` makes the form view reload after the button call (Odoo turns a
    `None` result into an `act_window_close` + `onClose` reload of the current form),
    so the row disappears while staying on the holder form.
  - The `_tms_document_check_critical` trip-start guard already uses
    `self.env["tms.document"].search(...)` which excludes `active = False` records —
    soft-deleted documents never block trip start.
- **Views** (`tms_driver_views.xml`, `fleet_vehicle_views.xml`) — render
  `document_ids` as an inline list with a per-row delete button:
  ```xml
  <field name="document_ids">
      <list>
          <field name="name" />
          <field name="doc_type" />
          <field name="expiry_date" />
          <field name="state" />
          <button name="action_soft_delete" type="object"
                  string="Delete" icon="fa-trash" confirm="Delete this document?" />
      </list>
  </field>
  ```

## Testing

- Update the three existing upload tests: assert the returned `ids` / `count` instead
  of the old action dict (`domain` / `view_mode` / `views`).
- New test: soft delete archives the document — `active` becomes `False`, it
  disappears from the holder's `document_ids`, and it no longer blocks
  `button_start_order`.
- Bump `19.0.1.0.3` → `19.0.1.0.4`.

## Out of scope

- No restore / unarchive UI (soft-deleted documents are fully hidden).
- No changes to the standalone Documents menu beyond what `active` already provides.
- Note: reloading the holder record discards any unsaved edits on the form; uploads /
  deletes happen on a saved record in practice.
