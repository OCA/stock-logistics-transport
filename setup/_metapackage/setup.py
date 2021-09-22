import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-stock-logistics-transport",
    description="Meta package for oca-stock-logistics-transport Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-stock_dock',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
