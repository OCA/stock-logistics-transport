def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE tms_order AS trip
           SET transport_type = vehicle.operation
          FROM fleet_vehicle AS vehicle
         WHERE trip.vehicle_id = vehicle.id
           AND trip.transport_type IS NULL
           AND vehicle.operation IN ('cargo', 'passenger')
        """
    )
    cr.execute(
        """
        UPDATE tms_order AS trip
           SET transport_type = team.operation
          FROM tms_team AS team
         WHERE trip.tms_team_id = team.id
           AND trip.transport_type IS NULL
           AND team.operation IN ('cargo', 'passenger')
        """
    )
