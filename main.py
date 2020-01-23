import argparse
from decimal import Decimal
from ServerValute.server import Server


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--rub", default=Decimal(0), action="store", type=Decimal)
    parser.add_argument("--usd", default=Decimal(0), action="store", type=Decimal)
    parser.add_argument("--eur", default=Decimal(0), action="store", type=Decimal)
    parser.add_argument("--period", default=5, action="store", type=int)
    parser.add_argument("--debug", default=False, action="store")  # , type=lambda x: x in [1, 'true', True, 'y', 'Y'])

    url = "https://www.cbr-xml-daily.ru/daily_utf8.xml"
    args = vars(parser.parse_args())
    server = Server({x: args[x] for x in ["rub", "usd", "eur"]},
                    url,
                    period=args["period"],
                    debug=args["debug"] in ['1', 'true', 'True', 'y', 'Y'])
    server.start()