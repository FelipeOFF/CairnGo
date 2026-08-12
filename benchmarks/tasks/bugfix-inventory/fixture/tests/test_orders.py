import unittest

from inventory import Inventory
from orders import fulfill_order


class TestOrders(unittest.TestCase):
    def setUp(self):
        self.inv = Inventory({"widget": 10, "gadget": 3})

    def test_fulfill_reduces_stock(self):
        fulfill_order(self.inv, [("widget", 4)])
        self.assertEqual(self.inv.available("widget"), 6)

    def test_fulfill_multiple_lines(self):
        fulfill_order(self.inv, [("widget", 2), ("gadget", 1)])
        self.assertEqual(self.inv.available("widget"), 8)
        self.assertEqual(self.inv.available("gadget"), 2)

    def test_insufficient_stock_raises(self):
        with self.assertRaises(ValueError):
            fulfill_order(self.inv, [("gadget", 5)])

    def test_insufficient_stock_leaves_inventory_unchanged(self):
        with self.assertRaises(ValueError):
            fulfill_order(self.inv, [("widget", 1), ("gadget", 5)])
        self.assertEqual(self.inv.available("widget"), 10)
        self.assertEqual(self.inv.available("gadget"), 3)


if __name__ == "__main__":
    unittest.main()
