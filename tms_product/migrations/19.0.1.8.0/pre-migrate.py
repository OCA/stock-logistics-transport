def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'product_template'
           AND column_name IN (
                'cargo_mode', 'transit_mode', 'transport_mode', 'booking_type'
           )
        """
    )
    columns = {row[0] for row in cr.fetchall()}
    if "booking_type" not in columns:
        cr.execute("ALTER TABLE product_template ADD COLUMN booking_type varchar")
    if "cargo_mode" in columns:
        cr.execute(
            """
            UPDATE product_template
               SET booking_type = CASE cargo_mode
                    WHEN 'ftl' THEN 'full_asset'
                    WHEN 'fcl' THEN 'full_asset'
                    WHEN 'vessel_charter' THEN 'full_asset'
                    WHEN 'air_charter' THEN 'full_asset'
                    WHEN 'ltl' THEN 'shared_space'
                    WHEN 'lcl' THEN 'shared_space'
                    WHEN 'air_consolidation' THEN 'shared_space'
                    WHEN 'back_to_back' THEN 'shared_space'
                    ELSE booking_type
                   END,
                   transit_mode = CASE cargo_mode
                    WHEN 'ftl' THEN 'road'
                    WHEN 'ltl' THEN 'road'
                    WHEN 'fcl' THEN 'water'
                    WHEN 'lcl' THEN 'water'
                    WHEN 'vessel_charter' THEN 'water'
                    WHEN 'air_charter' THEN 'air'
                    WHEN 'air_consolidation' THEN 'air'
                    WHEN 'back_to_back' THEN 'air'
                    ELSE transit_mode
                   END
             WHERE cargo_mode IS NOT NULL
            """
        )
    cr.execute(
        """
        UPDATE product_template
           SET booking_type = CASE transit_mode
                WHEN 'charter' THEN 'full_asset'
                WHEN 'cabin' THEN 'shared_space'
                WHEN 'seat' THEN 'shared_space'
                ELSE booking_type
               END
         WHERE transit_mode IN ('charter', 'cabin', 'seat')
        """
    )
    if "transport_mode" in columns:
        cr.execute(
            """
            UPDATE product_template
               SET transit_mode = transport_mode
             WHERE transit_mode IN ('charter', 'cabin', 'seat')
               AND transport_mode IN ('air', 'road', 'rail', 'water')
            """
        )
    cr.execute(
        """
        UPDATE product_template
           SET transit_mode = CASE
                WHEN transit_mode = 'charter' THEN 'road'
                WHEN transit_mode = 'cabin' THEN 'air'
                WHEN transit_mode = 'seat' THEN 'road'
                ELSE transit_mode
               END
         WHERE transit_mode IN ('charter', 'cabin', 'seat')
        """
    )
