def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE product_template
           SET transport_type = 'none'
         WHERE type = 'service'
           AND transport_type IS NULL
        """
    )
    cr.execute(
        """
        UPDATE product_template
           SET transit_mode = 'seat'
         WHERE transport_type = 'passenger'
           AND transit_mode IS NULL
        """
    )
