Enable **Order by Partner** on a shipment advice to create and reorder its
planned partner stops. The order is used when displaying planned transfers and
in shipment advice reports and emails.

The option is disabled by default. Disabling it removes the planned partner
stops and their sequences; enabling it again creates new stops.
For outgoing shipment advices, pickups and deliveries for the same partner
are separate stops. Transfers without a partner are grouped by operation type.

When upgrading an installation with the former per-transfer ordering, this
module is installed automatically. Ordering is enabled only on outgoing shipment
advices with more than one distinct partner, counting transfers without a partner
as one group. Transfers for the same partner and operation type inherit the
smallest former sequence for that group.
The original rows are retained in the ``shipment_advice_legacy_picking_order``
database table. Deleting a shipment advice or transfer also deletes its archived
orders. The former model and its metadata are removed.
Custom fields and integrations referencing it must be adapted to the new
partner-order model.
