def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'tms_rate_card'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'tms_rate_card'
           AND column_name IN ('booking_type', 'transport_type')
        """
    )
    columns = {row[0] for row in cr.fetchall()}
    if "booking_type" in columns:
        cr.execute(
            """
            UPDATE tms_rate_card
               SET booking_type = CASE booking_type
                    WHEN 'ftl' THEN 'full_asset'
                    WHEN 'charter' THEN 'full_asset'
                    WHEN 'ltl' THEN 'shared_space'
                    WHEN 'seat' THEN 'shared_space'
                    WHEN 'compartment' THEN 'shared_space'
                    ELSE booking_type
                   END
             WHERE booking_type IN (
                    'ftl', 'ltl', 'seat', 'compartment', 'charter'
                   )
            """
        )
    if "transport_type" not in columns:
        cr.execute("ALTER TABLE tms_rate_card ADD COLUMN transport_type varchar")
    cr.execute(
        """
        UPDATE tms_rate_card
           SET transport_type = 'cargo'
         WHERE transport_type IS NULL
        """
    )
