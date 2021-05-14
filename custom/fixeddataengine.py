# !/usr/bin/python
# vim: set fileencoding=utf8 :
#
__author__ = 'keping.chu'

import multiprocessing as mp
from threading import Thread

import aiohttp
import easyquotation

import time
from easyquant import PushBaseEngine
from easyquant.event_engine import Event
import numpy as np
import os
from datetime import date

class FixedDataEngine(PushBaseEngine):
    EventType = 'custom'
    PushInterval = 15
    BacktestEventType = 'backtest'
    Backtest = False

    def __init__(self, event_engine, clock_engine, watch_stocks=None, s='sina'):
        self.watch_stocks = watch_stocks
        self.s = s
        self.source = None
        self.__queue = mp.Queue(1000)
        self.is_pause = not clock_engine.is_tradetime_now()
        self._control_thread = Thread(
            target=self._process_control, name="FixedDataEngine._control_thread")
        self._control_thread.start()
        self.quotation_list = []
        self.stock_dick = {}
        if self.Backtest:
            self._init_backtest()
        super(FixedDataEngine, self).__init__(event_engine, clock_engine)

    def _init_backtest(self):
        dir_files = []
        t = date.today().isoformat()
        filedir = './data/{}'.format(t)
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
        # return self.source.stocks(self.watch_stocks, True)
        return self.source.all_market

    def push_quotation(self):
        if self.Backtest:                     
            event = Event(event_type=self.BacktestEventType, data=(self.stock_dick))
            self.event_engine.put(event)
            return

        while self.is_active:
            # if self.is_pause:
            #     time.sleep(1)
            #     continue
            try:
                response_data = self.fetch_quotation()
            except aiohttp.errors.ServerDisconnectedError:
                time.sleep(self.PushInterval)
                continue

            event = Event(event_type=self.EventType, data=response_data)
            self.event_engine.put(event)
            time.sleep(self.PushInterval)
