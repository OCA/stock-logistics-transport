def migrate(cr, version):
    """Drop the retired customer-tier records before the field is removed."""
    if not version:
        return
    names = (
        "menu_tms_customer_tier_sale",
        "tms_customer_tier_action",
        "tms_customer_tier_view_list",
        "view_partner_form_customer_tier",
    )
    cr.execute(
        """
        SELECT model, res_id
          FROM ir_model_data
         WHERE module = 'tms_sale'
           AND name IN %s
        """,
        (names,),
    )
    rows = cr.fetchall()
    tables = {
        "ir.ui.menu": "ir_ui_menu",
        "ir.actions.act_window": "ir_act_window",
        "ir.ui.view": "ir_ui_view",
    }
    order = {model: index for index, model in enumerate(tables)}
    for model, res_id in sorted(rows, key=lambda row: order.get(row[0], 9)):
        table = tables.get(model)
        if table:
            cr.execute(f'DELETE FROM "{table}" WHERE id = %s', (res_id,))
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'tms_sale'
           AND name IN %s
        """,
        (names,),
    )
