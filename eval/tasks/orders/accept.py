import unittest
from shop.pricing import invoice_total, format_money
from shop.report import daily_report
from shop.shipping import shipping_cost

LINES = [{'price': 40, 'qty': 2}, {'price': 20, 'qty': 1}]   # 100
TEN = {'type': 'percent', 'value': 10}


def order(country, voucher=None, lines=LINES):
    return {'id': 1, 'country': country, 'lines': lines, 'voucher': voucher}


class Accept(unittest.TestCase):
    def test_export_order_with_voucher_is_taxed_after_the_voucher(self):
        self.assertEqual(invoice_total(order('SK', TEN)), 120.0)   # 90 + 12 + 18
        self.assertEqual(invoice_total(order('DE', {'type': 'fixed', 'value': 30})), 94.3)
        self.assertEqual(invoice_total(order('US', {'type': 'percent', 'value': 50})), 81.5)

    def test_existing_behaviour_kept(self):
        self.assertEqual(invoice_total(order('IE')), 128.0)
        self.assertEqual(invoice_total(order('SK')), 132.0)
        self.assertEqual(invoice_total(order('IE', TEN)), 115.7)
        # free shipping is judged on the amount before the voucher
        big = [{'price': 160, 'qty': 1}]
        self.assertEqual(invoice_total(order('IE', {'type': 'percent', 'value': 20}, big)), 157.44)
        self.assertEqual(shipping_cost('IE', 200), 0)
        self.assertEqual(format_money(5), 'EUR 5')
        self.assertIn('orders: 2', daily_report([order('IE'), order('SK')]))
