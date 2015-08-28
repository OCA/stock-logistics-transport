.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

Shipment plan management (Consignment)
======================================

This module allows you to manage your transport.

A shipment plan (consignment) represents a kind of "contract" with your carrier and contains
the goods consigned together. It will show you the transit status of your deliveries or receptions,
help you monitor your goods in transit and provide an easy way of dealing with the dates of
departure and arrival.

Configuration
=============

To configure this module, you need to configure your Warehouse to use Transit Location

 * Go to *Warehouse/Configuration/Warehouse*
 * Edit your warehouse as follow:

   * **Incoming Shipments**: *Receive goods directly in stock from Transit (transit + 1 step)*

     and / or

   * **Outgoing Shippings**: *Ship from stock to Transit location*

You now have a new menu under *Warehouse/Shipment* to deal with your shipment plan.

Usage
=====

To create shipment plan, you need to:
-------------------------------------

 * Go to Picking list in *Warehouse/Operations/All Operations*

   or

 * Go to Move list in *Warehouse/Shipment/Waiting planification*

 * Select or Open some pickings/moves
 * Use **Add to a shipment** wizard

There, you will be able to create a new shipment or add selected moves to an existing shipment.
Only moves from the same source within same carrier can be bound together in a single shipment plan.

Confirm and send a shipment:
----------------------------

Once created the shipment plan must be confirmed. At that stage, you'll be able to load goods in
the consignment (by validating the departure pickings).

When the carrier comes and takes the consigned goods, the person in charge must click on
"Send to transit". There the system will:

 * If all departure pickings have been validated, mark the shipment plan as "In transit"
 * If not all departure pickings have been validated (e.g. all goods do not fit in the consignment),
   the system will warn you and if you still send the shipment plan, it will exclude the remaining
   goods so you can plan them in another shipment.

Receive a shipment:
-------------------

Upon reception, you'll be asked to validate all arrival pickings. All related moves must be
received to end the shipment plan workflow. In case not everything is here or you have damaged
goods, send them in a proper location (e.g lost in transit), so the shipment plan will be closed.

Monitor you goods in transit:
-----------------------------

From the menu *Warehouse/Shipment/In Transit* you can monitor what's in transit, what will arrive
when, etc..

On every shipment plan you can update the following information using the relevant "Update"
link on the form:

 * To Address
 * Consignee
 * Carrier
 * Tracking Ref.
 * ETD and ETA

 This information will be updated on all related pickings and logged in the chatter.

Known issues / Roadmap
======================

 * Being able to print necessary document from a given shipment plan (airway bill, packing list, etc..)


Credits
=======

Contributors
------------

* Yannick Vaucher <yannick.vaucher@camptocamp.com>
* Joël Grand-Guillaume <joel.grandguillaume@camptocamp.com>

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.

