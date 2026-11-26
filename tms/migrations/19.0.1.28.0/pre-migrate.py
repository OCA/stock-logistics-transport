# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Copy vehicle volume and payload onto the model when the model is empty."""
    if not version:
        return
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'fleet_vehicle'
           AND column_name IN ('capacity', 'weight_capacity')
        """
    )
    columns = {row[0] for row in cr.fetchall()}
    if "capacity" in columns:
        cr.execute(
            """
            UPDATE fleet_vehicle_model AS model
               SET max_volume_capacity = src.capacity,
                   max_volume_uom_id = COALESCE(
                       model.max_volume_uom_id, src.cargo_uom_id
                   )
              FROM (
                    SELECT DISTINCT ON (model_id)
                           model_id, capacity, cargo_uom_id
                      FROM fleet_vehicle
                     WHERE model_id IS NOT NULL
                       AND COALESCE(capacity, 0) <> 0
                     ORDER BY model_id, capacity DESC
                   ) AS src
             WHERE model.id = src.model_id
               AND COALESCE(model.max_volume_capacity, 0) = 0
            """
        )
    if "weight_capacity" in columns:
        cr.execute(
            """
            UPDATE fleet_vehicle_model AS model
               SET max_weight_capacity = src.weight_capacity,
                   max_weight_uom_id = COALESCE(
                       model.max_weight_uom_id, src.weight_uom_id
                   )
              FROM (
                    SELECT DISTINCT ON (model_id)
                           model_id, weight_capacity, weight_uom_id
                      FROM fleet_vehicle
                     WHERE model_id IS NOT NULL
                       AND COALESCE(weight_capacity, 0) <> 0
                     ORDER BY model_id, weight_capacity DESC
                   ) AS src
             WHERE model.id = src.model_id
               AND COALESCE(model.max_weight_capacity, 0) = 0
            """
        )
