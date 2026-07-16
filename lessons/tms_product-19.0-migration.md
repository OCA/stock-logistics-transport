# tms_product 19.0 migration (2026-06)

- Branch: `19.0-mig-tms_product` from `origin/19.0`; module history via
  `git format-patch origin/19.0..origin/17.0 -- tms_product`.
- `detailed_type` removed in Odoo 19 → use `type` on `product.template`.
- Views: `<tree>` → `<list>`; `views: [(False, "tree")]` → `[(False, "list")]`.
- UoM categories removed in Odoo 19 → use `res.config.settings._uom_hierarchy_domain()`
  / `_length_domain()` / `_weight_domain()` / `_volume_domain()` (same pattern as
  `tms`).
- Replace `_()` with `self.env._()`; add `_description` on `transportable.product`.
- `stock.move` no longer has `name` field in create vals (Odoo 19).
- Depends on `tms` migration PR (ursais/19.0-mig-tms) for CI.
