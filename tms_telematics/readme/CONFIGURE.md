Install a provider module, such as Geotab, and the OCA `queue_job` module.
Load `queue_job` in the server-wide modules and run Odoo with workers.
The pull cron queues one job per active account on the channel
`root.telematics`.

Create an account under Transport / Configuration / Telematics Accounts.
Set the provider, server, database, login, and password. The webhook
address is `/tms/telematics/hook/<account id>` and it expects the header
`X-Telematics-Token`.
