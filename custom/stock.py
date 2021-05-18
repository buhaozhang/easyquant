# !/usr/bin/python
# vim: set fileencoding=utf8 :
#
__author__ = 'zhangbuhao'

import time
from datetime import date
import numpy as np
from numpy.lib.function_base import quantile
import os
from threading import Lock


class Stock:
    Storage_Interval = 10

    def __init__(self, code, quotation = None):
        self.code = code
        self.date = date.today().isoformat()
        self.kline = []
        self.last_close = None
        self.open = None
        self.turnover = 0
        self.volume = 0
        self.high = 0
        self.low = 0
        self.avg_up_speed = 0
        self.avg_down_speed = 0
        self.lock = Lock()
        if quotation is not None:
            self.push_quotation(quotation)
            self.name = quotation['name']

    @property
    def last_stock(self):
        pass

    @property
    def close(self):
        pass

    def push_quotation(self, quotation):
        with self.lock:
            if self.date != quotation['date']:
                return
            self.last_close = quotation['close']
            self.open = quotation['open']
            bid_sum = quotation['bid1_volume'] + quotation['bid2_volume'] + \
                quotation['bid3_volume'] + \
                quotation['bid4_volume'] + quotation['bid5_volume']
            ask_sum = quotation['ask1_volume'] + quotation['ask2_volume'] + \
                quotation['ask3_volume'] + \
                quotation['ask4_volume'] + quotation['ask5_volume']
            wb = (bid_sum - ask_sum) / (bid_sum +
                                        ask_sum) if bid_sum + ask_sum > 0 else 0
            cur_q = [
                quotation['now'],
                quotation['buy'],
                quotation['sell'],
                quotation['turnover'] - self.turnover,
                quotation['volume'] - self.volume,
                wb,
                time.mktime(time.strptime('{} {}'.format(
                    quotation['date'], quotation['time']), '%Y-%m-%d %H:%M:%S'))
            ]
            if len(self.kline) > 0:
                last_q = self.kline[-1]
                last_t = last_q[-1]
                if int(cur_q[-1]) / self.Storage_Interval == int(last_t) / self.Storage_Interval:
                    cur_q[3] += last_q[3]
                    cur_q[4] += last_q[4]
                    self.kline[-1] = cur_q
                else:
                    self.kline.append(cur_q)
            else:
                self.kline.append(cur_q)
            self.turnover = quotation['turnover']
            self.volume = quotation['volume']
            self.high = quotation['high']
            self.low = quotation['low']

    def save(self):
        with self.lock:
            dir = os.path.join('data',format(self.date))
            # dir = './data/{}'.format(self.date)
            if not os.path.exists(dir):
                os.mkdir(dir)
            np.array(self.kline)
            np.save('./data/{}/{}'.format(date.today().isoformat(),
                    self.code), self.kline)

    @staticmethod
    def create_with_kline(code ,kline):
        stock = Stock(code)
        stock.kline = kline
        stock.last_close = stock.last_stock.close
        # for k in kline:
        #     self.open = 
        


    @staticmethod
    def read(file):
        dir = './data/{}'.format(date.today().isoformat())
        print('load ',file)
        kline = np.load(file)
        kline = kline.tolist()
        return Stock.create_with_kline(os.path.basename(file).split('.')[0],kline)

