def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'tms_telematics_reading_merge'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'tms_telematics_reading_merge'
           AND column_name = 'fuel_cost'
        """
    )
    if cr.fetchone():
        cr.execute(
            """
            UPDATE fleet_vehicle_odometer AS odometer
               SET fuel_cost = reading.fuel_cost,
                   expense_id = reading.expense_id
              FROM tms_telematics_reading_merge AS reading
             WHERE odometer.account_id = reading.account_id
               AND odometer.external_id = reading.external_id
            """
        )
    cr.execute("DROP TABLE tms_telematics_reading_merge")
