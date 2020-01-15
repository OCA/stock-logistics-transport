import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-stock-logistics-transport",
    description="Meta package for oca-stock-logistics-transport Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-stock_location_address',
        'odoo13-addon-stock_location_address_purchase',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
