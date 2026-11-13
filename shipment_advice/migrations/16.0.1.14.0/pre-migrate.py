from odoo.upgrade import util


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'shipment_advice_planned_partner_order'::regclass
            AND contype = 'u'
            AND pg_get_constraintdef(oid)
                = 'UNIQUE (shipment_advice_id, partner_id)'
        """
    )
    for (constraint_name,) in cr.fetchall():
        util.remove_constraint(
            cr,
            "shipment_advice_planned_partner_order",
            constraint_name,
            warn=False,
        )
