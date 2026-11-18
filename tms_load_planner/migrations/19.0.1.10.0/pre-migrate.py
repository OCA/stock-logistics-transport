def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'tms_vehicle_space'
           AND column_name = 'model_id'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        ALTER TABLE tms_cargo
        DROP CONSTRAINT IF EXISTS tms_cargo_vehicle_space_id_fkey
        """
    )
    cr.execute(
        """
        ALTER TABLE tms_trip_space_allocation
        DROP CONSTRAINT IF EXISTS tms_trip_space_allocation_vehicle_space_id_fkey
        """
    )
    cr.execute("ALTER TABLE tms_vehicle_space RENAME TO tms_vehicle_model_space")
    cr.execute(
        """
        ALTER SEQUENCE tms_vehicle_space_id_seq
        RENAME TO tms_vehicle_model_space_id_seq
        """
    )
    cr.execute(
        """
        ALTER TABLE tms_vehicle_model_space
        ALTER COLUMN id
        SET DEFAULT nextval('tms_vehicle_model_space_id_seq')
        """
    )
    cr.execute(
        """
        UPDATE ir_model_fields AS field
           SET model = 'tms.vehicle.model.space'
          FROM ir_model AS model
         WHERE field.model_id = model.id
           AND model.model = 'tms.vehicle.space'
        """
    )
    cr.execute(
        """
        UPDATE ir_model
           SET model = 'tms.vehicle.model.space'
         WHERE model = 'tms.vehicle.space'
        """
    )
    cr.execute(
        """
        UPDATE ir_model_fields
           SET relation = 'tms.vehicle.model.space'
         WHERE relation = 'tms.vehicle.space'
           AND name = 'space_ids'
        """
    )
    cr.execute(
        """
        UPDATE ir_model_data
           SET model = 'tms.vehicle.model.space'
         WHERE model = 'tms.vehicle.space'
        """
    )
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = replace(name, 'tms_vehicle_space', 'tms_vehicle_model_space')
         WHERE module = 'tms_load_planner'
           AND (
                name IN ('model_tms_vehicle_space', 'access_tms_vehicle_space_user')
                OR name LIKE 'field_tms_vehicle_space__%'
                OR name LIKE 'selection__tms_vehicle_space__%'
           )
        """
    )
    cr.execute(
        """
        CREATE TABLE tms_vehicle_space (
            id serial PRIMARY KEY,
            vehicle_id integer NOT NULL,
            model_space_id integer NOT NULL,
            state character varying NOT NULL DEFAULT 'available',
            create_uid integer,
            write_uid integer,
            create_date timestamp without time zone,
            write_date timestamp without time zone,
            CONSTRAINT tms_vehicle_space_vehicle_id_fkey
                FOREIGN KEY (vehicle_id)
                REFERENCES fleet_vehicle (id) ON DELETE CASCADE,
            CONSTRAINT tms_vehicle_space_model_space_id_fkey
                FOREIGN KEY (model_space_id)
                REFERENCES tms_vehicle_model_space (id) ON DELETE RESTRICT,
            CONSTRAINT tms_vehicle_space_create_uid_fkey
                FOREIGN KEY (create_uid)
                REFERENCES res_users (id) ON DELETE SET NULL,
            CONSTRAINT tms_vehicle_space_write_uid_fkey
                FOREIGN KEY (write_uid)
                REFERENCES res_users (id) ON DELETE SET NULL,
            CONSTRAINT tms_vehicle_space_vehicle_model_space_uniq
                UNIQUE (vehicle_id, model_space_id)
        )
        """
    )
    cr.execute(
        """
        CREATE INDEX tms_vehicle_space__vehicle_id_index
            ON tms_vehicle_space (vehicle_id)
        """
    )
    cr.execute(
        """
        CREATE INDEX tms_vehicle_space__model_space_id_index
            ON tms_vehicle_space (model_space_id)
        """
    )
    cr.execute(
        """
        CREATE INDEX tms_vehicle_space__state_index
            ON tms_vehicle_space (state)
        """
    )
    cr.execute(
        """
        INSERT INTO tms_vehicle_space (
            vehicle_id, model_space_id, state, create_date, write_date
        )
        SELECT vehicle.id,
               space.id,
               'available',
               (NOW() AT TIME ZONE 'UTC'),
               (NOW() AT TIME ZONE 'UTC')
          FROM fleet_vehicle AS vehicle
          JOIN tms_vehicle_model_space AS space
            ON space.model_id = vehicle.model_id
        """
    )
    cr.execute("ALTER TABLE tms_cargo ADD COLUMN tms_old_model_space_id integer")
    cr.execute(
        """
        UPDATE tms_cargo
           SET tms_old_model_space_id = vehicle_space_id
         WHERE vehicle_space_id IS NOT NULL
        """
    )
    cr.execute("UPDATE tms_cargo SET vehicle_space_id = NULL")
    cr.execute(
        """
        UPDATE tms_cargo AS cargo
           SET vehicle_space_id = space.id
          FROM tms_order AS trip
          JOIN tms_vehicle_space AS space ON space.vehicle_id = trip.vehicle_id
         WHERE cargo.order_id = trip.id
           AND space.model_space_id = cargo.tms_old_model_space_id
        """
    )
    cr.execute("ALTER TABLE tms_cargo DROP COLUMN tms_old_model_space_id")
    cr.execute(
        """
        ALTER TABLE tms_trip_space_allocation
        DROP CONSTRAINT IF EXISTS tms_trip_space_allocation_trip_space_uniq
        """
    )
    cr.execute(
        """
        ALTER TABLE tms_trip_space_allocation
        ALTER COLUMN vehicle_space_id DROP NOT NULL
        """
    )
    cr.execute(
        """
        ALTER TABLE tms_trip_space_allocation
        ADD COLUMN tms_old_model_space_id integer
        """
    )
    cr.execute(
        """
        UPDATE tms_trip_space_allocation
           SET tms_old_model_space_id = vehicle_space_id
        """
    )
    cr.execute(
        """
        UPDATE tms_trip_space_allocation
           SET vehicle_space_id = NULL
        """
    )
    cr.execute(
        """
        DELETE FROM tms_trip_space_allocation AS allocation
         WHERE NOT EXISTS (
            SELECT 1
              FROM tms_order AS trip
              JOIN tms_vehicle_space AS space
                ON space.vehicle_id = trip.vehicle_id
             WHERE trip.id = allocation.trip_id
               AND space.model_space_id = allocation.tms_old_model_space_id
         )
        """
    )
    cr.execute(
        """
        UPDATE tms_trip_space_allocation AS allocation
           SET vehicle_space_id = space.id
          FROM tms_order AS trip
          JOIN tms_vehicle_space AS space ON space.vehicle_id = trip.vehicle_id
         WHERE allocation.trip_id = trip.id
           AND space.model_space_id = allocation.tms_old_model_space_id
        """
    )
    cr.execute(
        """
        DELETE FROM tms_trip_space_allocation
         WHERE vehicle_space_id IS NULL
        """
    )
    cr.execute(
        """
        ALTER TABLE tms_trip_space_allocation
        ALTER COLUMN vehicle_space_id SET NOT NULL
        """
    )
    cr.execute(
        """
        ALTER TABLE tms_trip_space_allocation
          ADD CONSTRAINT tms_trip_space_allocation_trip_space_uniq
          UNIQUE (trip_id, vehicle_space_id)
        """
    )
    cr.execute(
        """
        ALTER TABLE tms_trip_space_allocation
        DROP COLUMN tms_old_model_space_id
        """
    )
    cr.execute(
        """
        UPDATE tms_trip_space_allocation
           SET state = 'available'
         WHERE state = 'held'
        """
    )
    cr.execute(
        """
        ALTER TABLE tms_cargo
          ADD CONSTRAINT tms_cargo_vehicle_space_id_fkey
          FOREIGN KEY (vehicle_space_id)
          REFERENCES tms_vehicle_space (id) ON DELETE SET NULL
        """
    )
    cr.execute(
        """
        ALTER TABLE tms_trip_space_allocation
          ADD CONSTRAINT tms_trip_space_allocation_vehicle_space_id_fkey
          FOREIGN KEY (vehicle_space_id)
          REFERENCES tms_vehicle_space (id) ON DELETE RESTRICT
        """
    )
