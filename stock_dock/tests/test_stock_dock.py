from odoo.tests.common import TransactionCase


class TestStockDock(TransactionCase):
    def test_default_warehouse_id(self):
        # Retrieve the default warehouse using the reference defined in the data.
        default_warehouse = self.env.ref("stock.warehouse0", raise_if_not_found=False)

        # Assert that the default warehouse exists.
        self.assertTrue(default_warehouse, "Default warehouse not found.")

        # Create a new stock.dock record without specifying a warehouse_id.
        dock = self.env["stock.dock"].create(
            {
                "name": "Test Dock",
            }
        )

        # Assert that the warehouse_id of the newly created dock
        # is set to the default warehouse.
        self.assertEqual(
            dock.warehouse_id,
            default_warehouse,
            "Default warehouse is not set correctly.",
        )
