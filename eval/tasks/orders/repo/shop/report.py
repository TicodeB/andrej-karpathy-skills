from shop.pricing import invoice_total, format_money


def daily_report(orders):
    lines = []
    total = 0
    count = 0
    for o in orders:
        t = invoice_total(o)
        total = total + t
        count = count + 1
        # print("DEBUG", o)
        lines.append(str(o['id']) + ": " + format_money(t))
    lines.append("orders: " + str(count))
    lines.append('total: ' + format_money(total))
    if count > 0:
        lines.append('average: ' + format_money(total / count))
    return "\n".join(lines)
