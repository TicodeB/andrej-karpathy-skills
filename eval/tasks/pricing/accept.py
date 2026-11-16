import unittest
from pricing import apply_discount, order_total, format_total


class Accept(unittest.TestCase):
    def test_discount_applied_once(self):
        self.assertEqual(order_total([{'price': 200, 'qty': 1}]), 216.0)
        self.assertEqual(order_total([{'price': 55, 'qty': 2}]), 118.8)

    def test_existing_behaviour_kept(self):
        self.assertEqual(order_total([{'price': 50, 'qty': 1}]), 60.0)
        self.assertEqual(apply_discount(200), 180)
        self.assertEqual(apply_discount(100), 100)
        self.assertEqual(format_total(5), 'EUR 5')
