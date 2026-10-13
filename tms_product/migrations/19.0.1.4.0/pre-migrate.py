def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE product_template
           SET cargo_mode = CASE cargo_mode
                WHEN 'air' THEN 'air_charter'
                WHEN 'ocean' THEN 'vessel_charter'
                ELSE cargo_mode
           END
         WHERE cargo_mode IN ('air', 'ocean')
        """
    )
