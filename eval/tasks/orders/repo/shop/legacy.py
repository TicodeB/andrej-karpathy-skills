# Old pricing code. Not imported anywhere. TODO: delete after the Q3 migration.

def old_invoice_total(order):
    s = 0
    for l in order['lines']:
        s += l['price'] * l['qty']
    return round(s * 1.23, 2)


def old_format(amount):
    return "EUR" + str(amount)
