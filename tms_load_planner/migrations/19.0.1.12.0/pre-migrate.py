# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Point each cargo at its trip space allocation."""
    if not version:
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'tms_cargo'
           AND column_name = 'vehicle_space_id'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        ALTER TABLE tms_cargo
        ADD COLUMN IF NOT EXISTS space_allocation_id INTEGER
        """
    )
    cr.execute(
        """
        UPDATE tms_cargo AS cargo
           SET space_allocation_id = allocation.id
          FROM tms_trip_space_allocation AS allocation
         WHERE allocation.cargo_id = cargo.id
           AND cargo.space_allocation_id IS NULL
        """
    )
    cr.execute(
        """
        UPDATE tms_cargo AS cargo
           SET space_allocation_id = allocation.id
          FROM tms_trip_space_allocation AS allocation
         WHERE cargo.space_allocation_id IS NULL
           AND cargo.vehicle_space_id IS NOT NULL
           AND cargo.order_id IS NOT NULL
           AND allocation.vehicle_space_id = cargo.vehicle_space_id
           AND allocation.trip_id = cargo.order_id
           AND NOT EXISTS (
                SELECT 1
                  FROM tms_cargo AS other
                 WHERE other.space_allocation_id = allocation.id
           )
        """
    )
