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
        INSERT INTO fleet_vehicle_odometer (
            vehicle_id, value, date,
            account_id, device_id, company_id, external_id, event,
            "timestamp", latitude, longitude, position_set, odometer_km,
            speed, speed_known, ignition, fuel_liters,
            create_uid, write_uid, create_date, write_date
        )
        SELECT
            reading.vehicle_id,
            COALESCE(reading.odometer_km, 0),
            COALESCE(reading.timestamp::date, CURRENT_DATE),
            reading.account_id,
            reading.device_id,
            reading.company_id,
            reading.external_id,
            reading.event,
            reading.timestamp,
            reading.latitude,
            reading.longitude,
            reading.position_set,
            reading.odometer_km,
            reading.speed,
            reading.speed_known,
            reading.ignition,
            reading.fuel_liters,
            COALESCE(reading.create_uid, 1),
            COALESCE(reading.write_uid, 1),
            COALESCE(reading.create_date, NOW() AT TIME ZONE 'UTC'),
            COALESCE(reading.write_date, NOW() AT TIME ZONE 'UTC')
        FROM tms_telematics_reading_merge AS reading
        WHERE reading.vehicle_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
                FROM fleet_vehicle_odometer AS existing
               WHERE existing.account_id = reading.account_id
                 AND existing.external_id = reading.external_id
          )
        """
    )
    cr.execute(
        """
        UPDATE ir_model_data AS data
           SET model = 'fleet.vehicle.odometer',
               res_id = odometer.id
          FROM tms_telematics_reading_merge AS reading
          JOIN fleet_vehicle_odometer AS odometer
            ON odometer.account_id = reading.account_id
           AND odometer.external_id = reading.external_id
         WHERE data.model = 'tms.telematics.reading'
           AND data.res_id = reading.id
        """
    )
    cr.execute(
        "SELECT state FROM ir_module_module WHERE name = 'tms_telematics_expense'"
    )
    row = cr.fetchone()
    if not row or row[0] not in ("installed", "to upgrade", "to install"):
        cr.execute("DROP TABLE tms_telematics_reading_merge")
