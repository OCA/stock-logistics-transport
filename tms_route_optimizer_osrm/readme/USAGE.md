After installing, the module automatically integrates with tms_route_optimizer.

Configuration
~~~~~~~~~~~~~

By default, the public OSRM server is used:
``https://router.project-osrm.org``

For production use, you can configure your own OSRM server:

1. Go to Settings > Technical > System Parameters
2. Find or create the key ``tms.osrm_server_url``
3. Set the URL to your OSRM server (e.g., ``http://osrm.mycompany.com:5000``)

Self-hosted OSRM
~~~~~~~~~~~~~~~~

For high-volume usage, consider running your own OSRM instance using Docker.
See https://github.com/Project-OSRM/osrm-backend for setup instructions.
