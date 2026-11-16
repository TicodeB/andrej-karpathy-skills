import json
import sys

from shop.pricing import invoice_total, format_money
from shop.report import daily_report


def main(argv):
    if len(argv) < 2:
        print("usage: cli.py orders.json [--report]")
        return 1
    orders = json.load(open(argv[1]))
    if '--report' in argv:
        print(daily_report(orders))
    else:
        for o in orders:
            print(o['id'], format_money(invoice_total(o)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
