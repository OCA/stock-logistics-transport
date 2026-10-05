def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE product_template
           SET invoice_policy = 'order'
         WHERE invoice_policy IS NULL
           AND id IN (
                SELECT res_id
                  FROM ir_model_data
                 WHERE module = 'tms_product'
                   AND model = 'product.template'
                   AND name LIKE 'product_tms_%'
           )
        """
    )
