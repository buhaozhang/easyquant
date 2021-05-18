# !/usr/bin/python
# vim: set fileencoding=utf8 :
#
__author__ = 'keping.chu'

from numpy.lib.function_base import quantile
from easytrader.xqtrader import XueQiuTrader
from threading import Thread
import queue
import aiohttp
import easyquotation
from .stock import Stock

import time,datetime
from easyquant import PushBaseEngine
from easyquant.event_engine import Event
import numpy as np
import os
from datetime import date
from queue import Queue, Empty
from dateutil import tz

class FixedDataEngine(PushBaseEngine):
    EventType = 'custom'
    PushInterval = 1
    BacktestEventType = 'backtest'
    Backtest = False
    Endurance = True

    def __init__(self, event_engine, clock_engine, watch_stocks=None, s='sina'):
        
        self.watch_stocks = watch_stocks
        self.s = s
        self.source = None
        self.__queue = queue.Queue()
        self.is_pause = not clock_engine.is_tradetime_now()
        
        self.quotation_list = []
        self.stock_dick = {}
        super(FixedDataEngine, self).__init__(event_engine, clock_engine)
        # self.read_stocks()
        self.__thread = Thread(target=self.__deal_quotation, name="FixedDataEngine.__deal_thread")
        
        if self.Backtest:
            self._init_backtest()
        if self.Endurance:
            clock_engine.register_interval(0.4, False, self.save_stocks)

        self.clock_engine.register_moment('t1', datetime.time(9, 10, 0,tzinfo=tz.tzlocal()), makeup=False,call=self.clear)
        self.clock_engine.register_moment('t2', datetime.time(12, 0, 0,tzinfo=tz.tzlocal()), makeup=False,call=self.save_stocks)
        self.clock_engine.register_moment('t3', datetime.time(15, 5, 0,tzinfo=tz.tzlocal()), makeup=False,call=self.save_stocks)

    def clear(self):
        self.__queue.put(None)

    def start(self):
        super(FixedDataEngine, self).start()
        self.__thread.start()

    def read_stock(self, code):
        return Stock.read(code)

    def read_stocks(self):
        dir_files = []
        t = date.today().isoformat()
        filedir = os.path.join('data',format(t))
        for root, dirs, files in os.walk(filedir):
            if root == filedir:
                for file in files:
                    dir_files.append(os.path.join(root, file))
        # self.read_stock(dir_files[0])
        res = self.source.pool.map(self.read_stock,dir_files)
        

    def deal_quotation(self,quotations):
        for code, quotation in quotations.items():
            stock = self.stock_dick.get(code, None)
            if stock is None:
                self.stock_dick[code] = Stock(code, quotation)
            else:
                stock.push_quotation(quotation)
        event = Event(event_type=self.EventType, data=(self.stock_dick,quotations))
        self.event_engine.put(event)

    def __deal_quotation(self):
        while self.is_active:
            try:
                quotations = self.__queue.get(block=True, timeout=5)
                if quotations is None:
                    self.stock_dick = {}
                else:
                    self.deal_quotation(quotations)
            except Empty:
                pass
        

    def save_stock(self, stock):
        stock.save()

    def save_stocks(self):
        res = self.source.pool.map(self.save_stock,self.stock_dick.values())

    def _init_backtest(self):
        dir_files = []
        t = date.today().isoformat()
        filedir = os.path.join('data',format(t))
        for root, dirs, files in os.walk(filedir):
            if root == filedir:
                for file in files:
                    dir_files.append(os.path.join(root, file))
        temp = {'name': '仁和药业', 'open': 9.09, 'close': 9.08, 'now': 9.33, 'high': 9.41, 'low': 8.81, 'buy': 9.33, 'sell': 9.34, 'turnover': 105191059, 'volume': 959620692.81, 'bid1_volume': 272899, 'bid1': 9.33, 'bid2_volume': 44200, 'bid2': 9.32, 'bid3_volume': 28100, 'bid3': 9.31,
                'bid4_volume': 194875, 'bid4': 9.3, 'bid5_volume': 59100, 'bid5': 9.29, 'ask1_volume': 87325, 'ask1': 9.34, 'ask2_volume': 358810, 'ask2': 9.35, 'ask3_volume': 60200, 'ask3': 9.36, 'ask4_volume': 133700, 'ask4': 9.37, 'ask5_volume': 183200, 'ask5': 9.38, 'date': '2021-05-12', 'time': '15:00:03'}
        for p in dir_files:
            code = os.path.basename(p).split('.')[0]
            np_list2 = np.load(p)
            self.stock_dick[code] = np_list2
            # i = 0
            # for np_list in np_list2:
            #     if len(self.quotation_list) <= i:
            #         self.quotation_list.append({})
            #     event_data = self.quotation_list[i]
            #     t = temp.copy()
            #     j = 0
            #     datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(np_list[-1])).split(' ')
            #     for k in t.keys():
            #         if k == 'name':
            #             t[k] = code
            #             continue
            #         if k == 'date':
            #             t[k] = datetime[0]
            #             continue
            #         if k == 'time':
            #             t[k] = datetime[1]
            #             continue
            #         t[k] = np_list[j]
            #         j += 1
            #     event_data[code] = t
            #     i += 1
        # print(self.quotation_list)

    def _process_control(self):

        while True:
            try:
                msg = self.__queue.get(block=True)
                if msg == "pause":
                    self.is_pause = True
                else:
                    self.is_pause = False
            except:
                pass

    def pause(self):
        self.__queue.put("pause")

    def work(self):
        self.__queue.put("work")

    def init(self):
        # 进行相关的初始化操作
        self.source = easyquotation.use(self.s)

    def fetch_quotation(self):
        # 返回行情
        if self.Endurance:
            return self.source.all_market
        else:
            return self.source.stocks(self.watch_stocks, True)

    def push_quotation(self):
        if self.Backtest:
            event = Event(event_type=self.BacktestEventType,
                          data=(self.stock_dick))
            self.event_engine.put(event)
            return

        while self.is_active:
            # if self.is_pause:
            #     time.sleep(1)
            #     continue
            try:
                response_data = self.fetch_quotation()
            except Exception as e:
                print(e)
                time.sleep(self.PushInterval)
                continue
            print(time.time())
            print(len(response_data))
            self.__queue.put(response_data)
            time.sleep(self.PushInterval)
