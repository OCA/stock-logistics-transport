Install a provider module, such as Geotab, and the OCA `queue_job` module.
Load `queue_job` in the server-wide modules and run Odoo with workers.
The pull cron queues one job per active account on the channel
`root.telematics`.

Create an account under Transport / Configuration / Telematics Accounts.
Set the provider, server, database, login, and password. Turn on
Create vehicles and choose a vehicle model when a device should create
its fleet vehicle if none matches the VIN or the license plate. Leave
it off to link devices only to vehicles that already exist. The webhook
address is `/tms/telematics/hook/<account id>` and it expects the header
`X-Telematics-Token`.
