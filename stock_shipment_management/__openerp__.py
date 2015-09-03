# -*- coding: utf-8 -*-
#
#
#    Authors: Joël Grand-Guillaume, Yannick Vaucher
#    Copyright 2013-2015 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more description.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
{"name": "Shipment Management (Consignment)",
 "version": "8.0.1.0.2",
 "author": "Camptocamp,Odoo Community Association (OCA)",
 "category": "Transportation",
 "license": 'AGPL-3',
 "complexity": "normal",
 "images": [],
 "website": "http://www.camptocamp.com",
 "depends": ["delivery",
             "stock_route_transit",
             "transport_information",
             "sale_transport_multi_address",
             "purchase_transport_multi_address",
             ],
 "demo": [],
 "data": ["data/shipment_plan_sequence.xml",
          "wizard/shipment_carrier_setter_view.xml",
          "wizard/shipment_carrier_tracking_ref_setter_view.xml",
          "wizard/shipment_consignee_setter_view.xml",
          "wizard/shipment_etd_setter_view.xml",
          "wizard/shipment_eta_setter_view.xml",
          "wizard/shipment_to_address_setter_view.xml",
          "wizard/create_shipment_view.xml",
          "wizard/shipment_transit_confirm_view.xml",
          "view/menu.xml",
          "view/shipment_plan.xml",
          "view/stock_move.xml",
          "view/sale_order.xml",
          "view/purchase_order.xml",
          "workflow/shipment_plan.xml",
          "security/ir.model.access.csv",
          ],
 "auto_install": False,
 "test": [],
 "installable": True,
 }
