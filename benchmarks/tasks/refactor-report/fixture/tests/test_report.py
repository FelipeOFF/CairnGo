import unittest

from report import total_sales, total_refunds, total_tax


class TestReport(unittest.TestCase):
    def setUp(self):
        self.records = [
            {"kind": "sale", "amount": 100},
            {"kind": "sale", "amount": 50},
            {"kind": "refund", "amount": 20},
            {"kind": "tax", "amount": 8},
            {"kind": "tax", "amount": 2},
        ]

    def test_total_sales(self):
        self.assertEqual(total_sales(self.records), 150)

    def test_total_refunds(self):
        self.assertEqual(total_refunds(self.records), 20)

    def test_total_tax(self):
        self.assertEqual(total_tax(self.records), 10)

    def test_empty_records(self):
        self.assertEqual(total_sales([]), 0)
        self.assertEqual(total_refunds([]), 0)
        self.assertEqual(total_tax([]), 0)


if __name__ == "__main__":
    unittest.main()
