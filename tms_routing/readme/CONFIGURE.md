Install a provider module, such as OpenRouteService, and the OCA
`queue_job` module. Load `queue_job` in the server-wide modules and run
Odoo with workers. The compute job uses the channel `root.routing`.

On the route, choose the provider. Enable **Avoid tolls** when the path
must stay off toll roads.
