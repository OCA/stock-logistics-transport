Enable **Order by Partner** on a shipment advice to create and reorder its
planned partner stops. The order is used when displaying planned transfers and
in shipment advice reports and emails.

The option is disabled by default. Disabling it removes the planned partner
stops and their sequences; enabling it again creates new stops.

When upgrading an installation with the former per-transfer ordering, this
module is installed automatically. Ordering is enabled only on outgoing shipment
advices with more than one distinct partner, counting transfers without a partner
as one group. Transfers in the same group inherit the smallest former sequence.
The original rows are retained in the ``shipment_advice_legacy_picking_order``
database table without foreign keys; their identifiers may no longer correspond
to existing records after deletion. The former model and its metadata are removed.
Custom fields and integrations referencing it must be adapted to the new
partner-order model.
