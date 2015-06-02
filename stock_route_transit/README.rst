.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Stock Route Transit
===================

This addon adds Transit route configuration facility for warehouses by adding
new possible values for the reception_steps and delivery_steps fields of
stock.warehouse. It does nothing that could not be done manually, but the
manual configuration of these routes is long, tedious and error prone, which is
why the reception_steps and delivery_steps fields were added in the first place
in Odoo.

When configuring a reception (resp. delivery) with transit, the goods shipped
by the supplier (rest. to the customer) first go to a transit stock.location
before reaching their final destination. This allows for tracking the shipping
date separately from the delivery date, as well as managing incidents which can
occure during transport.

When this module is installed and configured on a warehouse, displaying the
pickings of a Purchase Order will only show the picking from Supplier to
Transit. To change that you may install `purchase_all_shipments` from
https://github.com/OCA/purchase-workflow


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/stock-logistics-transport/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/stock-logistics-transport/issues/new?body=module:%20stock_route_transit%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


Credits
=======

Contributors
------------

* Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
* Joël Grand-Guillaume <joel.grandguillaume@camptocamp.com>
* Leonardo Pistone <leonardo.pistone@camptocamp.com>
* Pedro M. Baeza <pedro.baeza@gmail.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.

