The expiry horizon is controlled by the configuration parameter
`tms.document.expiry_horizon_days` (default: **30** days).

A document whose expiry date is within this many days is considered
*expiring*; once the expiry date passes, it is *expired*.

To change the horizon, set the parameter under *Settings > Technical >
Parameters* (or via `ir.config_parameter.set_param`). A smaller value makes
documents switch to *expiring* later; a larger value warns earlier.
