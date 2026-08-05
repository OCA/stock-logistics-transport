Generic, expiry-tracked document framework for the TMS.

Attach typed documents (license, insurance, inspection, ...) to any TMS
resource (drivers, vehicles). Document validity (valid / expiring / expired)
is computed from the expiry date against a configurable horizon.

A document can be flagged *critical*: an expired critical document on a
trip's driver or vehicle blocks starting that trip.
