def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'product_template'
           AND column_name = 'tms_trip'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        "ALTER TABLE product_template "
        "ADD COLUMN IF NOT EXISTS transport_type varchar"
    )
    cr.execute(
        """
        UPDATE product_template
           SET transport_type = CASE
                   WHEN trip_product_type = 'seat' THEN 'passenger'
                   ELSE 'cargo'
               END
         WHERE COALESCE(tms_trip, FALSE)
           AND transport_type IS NULL
        """
    )
