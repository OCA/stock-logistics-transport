
[![Runboat](https://img.shields.io/badge/runboat-Try%20me-875A7B.png)](https://runboat.odoo-community.org/builds?repo=OCA/stock-logistics-transport&target_branch=17.0)
[![Pre-commit Status](https://github.com/OCA/stock-logistics-transport/actions/workflows/pre-commit.yml/badge.svg?branch=17.0)](https://github.com/OCA/stock-logistics-transport/actions/workflows/pre-commit.yml?query=branch%3A17.0)
[![Build Status](https://github.com/OCA/stock-logistics-transport/actions/workflows/test.yml/badge.svg?branch=17.0)](https://github.com/OCA/stock-logistics-transport/actions/workflows/test.yml?query=branch%3A17.0)
[![codecov](https://codecov.io/gh/OCA/stock-logistics-transport/branch/17.0/graph/badge.svg)](https://codecov.io/gh/OCA/stock-logistics-transport)
[![Translation Status](https://translation.odoo-community.org/widgets/stock-logistics-transport-17-0/-/svg-badge.svg)](https://translation.odoo-community.org/engage/stock-logistics-transport-17-0/?utm_source=widget)

<!-- /!\ do not modify above this line -->

# stock-logistics-transport

TODO: add repo description.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

Available addons
----------------
addon | version | maintainers | summary
--- | --- | --- | ---
[stock_location_address](stock_location_address/) | 17.0.1.0.0 |  | Adds an address on locations
[tms](tms/) | 17.0.1.1.0 | <a href='https://github.com/max3903'><img src='https://github.com/max3903.png' width='32' height='32' style='border-radius:50%;' alt='max3903'/></a> <a href='https://github.com/santiagordz'><img src='https://github.com/santiagordz.png' width='32' height='32' style='border-radius:50%;' alt='santiagordz'/></a> <a href='https://github.com/EdgarRetes'><img src='https://github.com/EdgarRetes.png' width='32' height='32' style='border-radius:50%;' alt='EdgarRetes'/></a> | Manage Vehicles, Drivers, Routes and Trips
[tms_account](tms_account/) | 17.0.1.0.0 | <a href='https://github.com/max3903'><img src='https://github.com/max3903.png' width='32' height='32' style='border-radius:50%;' alt='max3903'/></a> <a href='https://github.com/santiagordz'><img src='https://github.com/santiagordz.png' width='32' height='32' style='border-radius:50%;' alt='santiagordz'/></a> <a href='https://github.com/EdgarRetes'><img src='https://github.com/EdgarRetes.png' width='32' height='32' style='border-radius:50%;' alt='EdgarRetes'/></a> | Track invoices linked to TMS orders
[tms_account_asset](tms_account_asset/) | 17.0.1.0.0 | <a href='https://github.com/max3903'><img src='https://github.com/max3903.png' width='32' height='32' style='border-radius:50%;' alt='max3903'/></a> <a href='https://github.com/santiagordz'><img src='https://github.com/santiagordz.png' width='32' height='32' style='border-radius:50%;' alt='santiagordz'/></a> <a href='https://github.com/EdgarRetes'><img src='https://github.com/EdgarRetes.png' width='32' height='32' style='border-radius:50%;' alt='EdgarRetes'/></a> | Manage TMS assets
[tms_expense](tms_expense/) | 17.0.1.0.0 | <a href='https://github.com/max3903'><img src='https://github.com/max3903.png' width='32' height='32' style='border-radius:50%;' alt='max3903'/></a> <a href='https://github.com/santiagordz'><img src='https://github.com/santiagordz.png' width='32' height='32' style='border-radius:50%;' alt='santiagordz'/></a> <a href='https://github.com/EdgarRetes'><img src='https://github.com/EdgarRetes.png' width='32' height='32' style='border-radius:50%;' alt='EdgarRetes'/></a> | Manage expenses of a trip: hotel, tolls, fuel
[tms_product](tms_product/) | 17.0.1.0.0 | <a href='https://github.com/max3903'><img src='https://github.com/max3903.png' width='32' height='32' style='border-radius:50%;' alt='max3903'/></a> <a href='https://github.com/santiagordz'><img src='https://github.com/santiagordz.png' width='32' height='32' style='border-radius:50%;' alt='santiagordz'/></a> <a href='https://github.com/EdgarRetes'><img src='https://github.com/EdgarRetes.png' width='32' height='32' style='border-radius:50%;' alt='EdgarRetes'/></a> | Manage Vehicles as Products
[tms_purchase](tms_purchase/) | 17.0.1.0.0 | <a href='https://github.com/max3903'><img src='https://github.com/max3903.png' width='32' height='32' style='border-radius:50%;' alt='max3903'/></a> <a href='https://github.com/santiagordz'><img src='https://github.com/santiagordz.png' width='32' height='32' style='border-radius:50%;' alt='santiagordz'/></a> <a href='https://github.com/EdgarRetes'><img src='https://github.com/EdgarRetes.png' width='32' height='32' style='border-radius:50%;' alt='EdgarRetes'/></a> | Manage purchase requests to drivers and other suppliers
[tms_sale](tms_sale/) | 17.0.1.0.1 | <a href='https://github.com/max3903'><img src='https://github.com/max3903.png' width='32' height='32' style='border-radius:50%;' alt='max3903'/></a> <a href='https://github.com/santiagordz'><img src='https://github.com/santiagordz.png' width='32' height='32' style='border-radius:50%;' alt='santiagordz'/></a> <a href='https://github.com/EdgarRetes'><img src='https://github.com/EdgarRetes.png' width='32' height='32' style='border-radius:50%;' alt='EdgarRetes'/></a> | Sell transportation management system.

[//]: # (end addons)

<!-- prettier-ignore-end -->

## Licenses

This repository is licensed under [AGPL-3.0](LICENSE).

However, each module can have a totally different license, as long as they adhere to Odoo Community Association (OCA)
policy. Consult each module's `__manifest__.py` file, which contains a `license` key
that explains its license.

----
OCA, or the [Odoo Community Association](http://odoo-community.org/), is a nonprofit
organization whose mission is to support the collaborative development of Odoo features
and promote its widespread use.
