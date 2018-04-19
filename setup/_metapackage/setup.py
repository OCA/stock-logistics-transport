import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo8-addons-oca-stock-logistics-transport",
    description="Meta package for oca-stock-logistics-transport Odoo addons",
    version=version,
    install_requires=[
        'odoo8-addon-purchase_requisition_transport_multi_address',
        'odoo8-addon-purchase_transport_multi_address',
        'odoo8-addon-sale_transport_multi_address',
        'odoo8-addon-stock_route_transit',
        'odoo8-addon-stock_shipment_management',
        'odoo8-addon-stock_transport_multi_address',
        'odoo8-addon-transport_information',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
