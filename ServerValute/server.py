from decimal import Decimal
from itertools import combinations

import logging
import asyncio
import aiohttp
from aiohttp import web
from lxml import etree


class Server:
    def __init__(self, init_counts: dict, url: str, period=1, debug=True):
        self.period = period
        self.counts = init_counts
        self.url = url
        self.rates = {'rub': Decimal(1)}
        self.loop = asyncio.get_event_loop()

        self.cache = {'rates': self.rates.copy(), 'counts': self.counts.copy()}

        level = logging.INFO
        if debug:
            level = logging.DEBUG
        logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(message)s', level=level)

    async def get_rates(self):
        while True:
            async with aiohttp.request('GET', self.url) as response:
                logging.debug(f'Содержимое Request:\n{response.request_info.url}\n{response.request_info.headers}')
                xml_text = await response.content.read()
                logging.debug(f'Содержимое Response:\n{xml_text.decode("utf-8")}')

                root = etree.fromstring(xml_text)
                for valute in self.counts:
                    if valute == 'rub':
                        continue
                    xpath = f'.//Valute/CharCode[text()="{valute.upper()}"]/../Value/text()'
                    value = root.xpath(xpath)[0]
                    self.rates[valute] = Decimal(value.replace(',', '.'))

                logging.info(msg=f'Данные о курсах обновлены\n{self.rates}')

            await asyncio.sleep(self.period * 60)

    def total_valute(self, valute):
        return sum([self.rates[val] * self.counts[val] for val in self.counts])/self.rates[valute]

    async def get_amount(self, request):
        res_text = ""
        valute = request.match_info.get('valute', 'NoneValute')
        if valute == 'amount':
            res_text += ' '.join(f'{v}: {self.counts[v]}' for v in self.counts)
            res_text += '\n'
            for v1, v2 in combinations(self.counts, 2):
                if self.rates[v1] < self.rates[v2]:
                    v1, v2 = v2, v1  # To make rate >= 1
                res_text += f'{v1}-{v2}: {self.rates[v1]/self.rates[v2]:.4f} '
            res_text += '\nSum: '
            res_text += ' / '.join(f'{self.total_valute(v):.2f} {v}' for v in self.counts)
        elif valute in self.counts:
            res_text = f"{valute}: {self.counts[valute]}\n"
            for v1 in self.counts:
                if v1 == valute:
                    continue
                v2 = valute
                if self.rates[v1] < self.rates[v2]:
                    v1, v2 = v2, v1  # To make rate >= 1
                res_text += f'{v1}-{v2}: {self.rates[v1] / self.rates[v2]:.4f} '
            res_text += '\nSum: '
            res_text += f'{self.total_valute(valute):.2f} {valute}'
        return web.Response(text=res_text, headers={'content-type': 'text/plain'})

    async def set_amount(self, request):
        responce = await request.json()
        for v in responce:
            if v in self.counts:
                self.counts[v] = responce[v]
        return web.Response(text="Изменено", headers={'content-type': 'text/plain'})

    async def modify_amount(self, request):
        responce = await request.json()
        for v in responce:
            if v in self.counts:
                self.counts[v] += responce[v]
        return web.Response(text="Изменено", headers={'content-type': 'text/plain'})

    async def run_listen_server(self):
        app = web.Application()
        app.add_routes([
            web.get('/{valute}/get', self.get_amount),
            web.post('/amount/set', self.set_amount),
            web.post('/amount/modify', self.modify_amount),
        ])

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner)
        await site.start()

    async def print_valutes(self):
        while True:
            if self.cache['rates'] != self.rates or self.cache['counts'] != self.counts:
                logging.info(f'Текущий счет: {self.counts}')
                self.cache['rates'] = self.rates.copy()
                self.cache['counts'] = self.counts.copy()
            # else:
            #     logging.debug('нет изменений')
            await asyncio.sleep(4)

    def start(self):
        logging.info('Сервер запущен')
        self.loop.run_until_complete(
            asyncio.gather(*[self.get_rates(), self.run_listen_server(), self.print_valutes()])
        )
        self.loop.close()



