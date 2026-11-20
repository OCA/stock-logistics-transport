# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo.upgrade import util

OLD_TABLE = "shipment_advice_planned_picking_order"
ARCHIVE_TABLE = "shipment_advice_legacy_picking_order"


def _update_mail_template(cr):
    template_filter = """
        t.id IN (
            SELECT res_id FROM ir_model_data
             WHERE module = 'shipment_advice'
               AND name = 'email_template_shipment_advice'
               AND model = 'mail.template'
        )
    """
    for old_expression in (
        "object.planned_picking_ids.sorted(lambda picking: "
        "picking.with_context(active_shipment_advice_id=object.id)"
        ".sequence_in_shipment_advice)",
        "object.planned_picking_ids.sorted(lambda picking: "
        "picking.with_context(active_shipment_advice_id=object.id)"
        ".shipment_advice_sort_key)",
    ):
        util.replace_in_all_jsonb_values(
            cr,
            "mail_template",
            "body_html",
            old_expression,
            "object._get_email_planned_pickings()",
            extra_filter=template_filter,
        )


def _archive_old_table(cr):
    old_exists = util.table_exists(cr, OLD_TABLE)
    archive_exists = util.table_exists(cr, ARCHIVE_TABLE)
    if not old_exists and not archive_exists:
        return
    if old_exists and archive_exists:
        raise RuntimeError("The shipment advice picking order archive already exists")

    # Prevent data loss by archiving the old table.
    if old_exists:
        cr.execute(
            "ALTER TABLE shipment_advice_planned_picking_order "
            "RENAME TO shipment_advice_legacy_picking_order"
        )


def _force_install_shipment_advice_partner_sorting(cr):
    state = util.force_install_module(
        cr,
        "shipment_advice_partner_sorting",
        reason="preserve existing shipment advice picking sequences",
    )
    if state not in ("installed", "to install", "to upgrade"):
        raise RuntimeError(
            "shipment_advice_partner_sorting must be available before upgrading "
            "shipment_advice"
        )


def _declare_partner_sorting(cr):
    # Declare the partner_sorting_enabled column for shipment advice
    # We set this column to TRUE for shipment advice records that have multiple
    # partners in their legacy picking orders.
    util.create_column(cr, "shipment_advice", "partner_sorting_enabled", "boolean")
    archive_exists = util.table_exists(cr, ARCHIVE_TABLE)
    if not archive_exists:
        return
    cr.execute(
        """
        UPDATE shipment_advice advice
           SET partner_sorting_enabled = TRUE
         WHERE advice.shipment_type = 'outgoing'
           AND EXISTS (
               SELECT old_order.shipment_advice_id
                 FROM shipment_advice_legacy_picking_order old_order
                 JOIN stock_picking picking ON picking.id = old_order.stock_picking_id
                WHERE old_order.shipment_advice_id = advice.id
                GROUP BY old_order.shipment_advice_id
               HAVING COUNT(DISTINCT COALESCE(picking.partner_id, 0)) > 1
         )
        """
    )


def migrate(cr, version):
    if not version:
        return
    _update_mail_template(cr)
    _archive_old_table(cr)
    _force_install_shipment_advice_partner_sorting(cr)
    _declare_partner_sorting(cr)
