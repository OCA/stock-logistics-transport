import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-stock-logistics-transport",
    description="Meta package for oca-stock-logistics-transport Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-shipment_advice>=16.0dev,<16.1dev',
        'odoo-addon-shipment_advice_planner>=16.0dev,<16.1dev',
        'odoo-addon-shipment_advice_planner_toursolver>=16.0dev,<16.1dev',
        'odoo-addon-shipment_advice_planner_toursolver_queue_job>=16.0dev,<16.1dev',
        'odoo-addon-stock_dock>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
