import math, sys
from shop.shipping import shipping_cost

VAT = 0.23
EXPORT_VAT = {'SK': 0.20, 'DE': 0.19, "FR": 0.20, 'GB': 0.20}


def subtotal(lines):
    total = 0
    for l in lines:
        total = total + l['price'] * l['qty']
    return total


def apply_voucher( amount, voucher ):
    # vouchers: {'type': 'percent'|'fixed', 'value': n}
    if voucher == None:
        return amount
    else:
        if voucher['type'] == "percent":
            return amount - amount * voucher['value'] / 100
        else:
            if voucher['type'] == 'fixed':
                return max(amount - voucher["value"], 0)
            else:
                return amount


def invoice_total(order):
    sub = subtotal(order['lines'])
    discounted = apply_voucher(sub, order.get('voucher'))
    ship = shipping_cost(order['country'], sub)
    if order['country'] == 'IE':
        tax = discounted * VAT
    else:
        # export orders are taxed at the destination rate
        tax = sub * EXPORT_VAT.get(order['country'], VAT)
    return round(discounted + ship + tax, 2)


def format_money(amount, currency='EUR'):
    # fromat with 2 decimals
    return currency + " " + str(round(amount, 2))
