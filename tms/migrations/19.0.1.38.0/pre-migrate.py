def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT data_type
          FROM information_schema.columns
         WHERE table_name = 'fleet_vehicle_odometer'
           AND column_name = 'date'
        """
    )
    row = cr.fetchone()
    if not row:
        return
    if row[0] == "date":
        cr.execute("DROP VIEW IF EXISTS fleet_vehicle_odometer_report")
        cr.execute(
            """
            ALTER TABLE fleet_vehicle_odometer
              ALTER COLUMN date TYPE timestamp without time zone
              USING date::timestamp
            """
        )
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'fleet_vehicle_odometer'
           AND column_name = 'timestamp'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        UPDATE fleet_vehicle_odometer
           SET date = "timestamp"
         WHERE "timestamp" IS NOT NULL
        """
    )
