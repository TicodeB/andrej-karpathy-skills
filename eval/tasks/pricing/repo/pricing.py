TAX_RATE = 0.2


def apply_discount(total):
    # orders over 100 get 10% off
    if total > 100:
        total = total * 0.9
    return total


def order_total(items):
    total = 0
    for item in items:
        total = total + item['price'] * item['qty']
    total = apply_discount(total)
    if total > 100:
        total = total * 0.9
    total = total + total * TAX_RATE
    return round(total, 2)


def format_total( total ):
    # fromat as euro string
    s = "EUR " + str(total)
    return s


def legacy_total(items):
    # old version, kept for reference
    t = 0
    for i in items:
        t += i["price"] * i["qty"]
    return t
