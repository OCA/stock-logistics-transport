Shipment plan management (Consignment)
======================================

This module allows you to manage your transport.

A shipment plan (consignment) represent a kind of "contract" with your carrier and contain
the goods consigned together. It will show you show you transit status of your deliveries 
or reception, help you monitor your goods in transit and provide an easy way of dealing
the the dates of departure and arrival.

Configuration
=============

To configure this module, you need to configure your Warehouse to use Transit Location

 * Go to *Warehouse/Configuration/Warehouse*
 * Edit your warehouse as follow:

   * **Incoming Shipments**: *Receive goods directly in stock from Transit (transit + 1 step)*

     and / or

   * **Outgoing Shippings**: *Ship from stock to Transit location*

You now have a new menu under *Warehouse/Shipment* to deal with your shipment plan,

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
Only moves from same source within same carrier can be bound together in a same shipment plan.

Confirm and send a shipment:
----------------------------

Once created the shipment plan must be confirm. At that stage, you'll able to load goods in the 
consignment(by validating the departure pickings). 

When the carrier comes and takes the consigned goods, the person in charge must click on 
"Send to transit". There the system will:
 * If all departure pickings have been validated, mark the shipment plan as "In transit"
 * If not all departure picking have been validated (e.g. all goods do not fit in the consignment),
   the system will warn you and if you still sent the shipment plan, he will exclude the remaining
   goods so you can plan them in another shipment.

Reception a shipment:
---------------------

At the reception, you'll be asked to validate all arrival pickings. All related moves must be 
receptioned to end the shipment plan workflow. In case not everything is here or you have damaged
goods, send them in a proper location (e.g lost in transit), so the shipment plan will be closed.

Monitor you goods in transit:
-----------------------------

From the menu *Warehouse/Shipment/In Transit* you can monitor what's in transit, what will arrive 
when, etc..

On every shipment plan you can update the following informations using the relevant "Update" 
link on the form:

 * To Address
 * Consignee
 * Carrier
 * Tracking Ref.
 * ETD and ETA

 Those informations will be update on all related pickings and loged in the chatter.

Known issues / Roadmap
======================

 * Being able to print necessary document from a given shipment plan (airway bill, packing list, etc..)


Credits
=======

Contributors
------------

* Yannick Vaucher <yannick.vaucher@camptocamp.com>
* Joel Grand-Guillaume <joel.grandguillaume@camptocamp.com>

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.

