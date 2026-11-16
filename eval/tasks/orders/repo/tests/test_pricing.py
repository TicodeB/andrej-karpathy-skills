import unittest
from shop.pricing import subtotal, apply_voucher, invoice_total

LINES = [{'price': 40, 'qty': 2}, {'price': 20, 'qty': 1}]   # 100


class TestPricing(unittest.TestCase):
    def test_subtotal(self):
        self.assertEqual(subtotal(LINES), 100)

    def test_percent_voucher(self):
        self.assertEqual(apply_voucher(100, {'type': 'percent', 'value': 10}), 90)

    def test_fixed_voucher(self):
        self.assertEqual(apply_voucher(100, {"type": "fixed", "value": 30}), 70)

    def test_irish_order(self):
        order = {'id': 1, 'country': 'IE', 'lines': LINES}
        self.assertEqual(invoice_total(order), 128.0)   # 100 + 5 + 23

    def test_export_order(self):
        order = {'id': 2, 'country': 'SK', 'lines': LINES}
        self.assertEqual(invoice_total(order), 132.0)   # 100 + 12 + 20
