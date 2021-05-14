import time
from datetime import date
import datetime as dt
from dateutil import tz
from easyquant import DefaultLogHandler
from easyquant import StrategyTemplate
import numpy as np
import pandas as pd
import os
"""
买入：
    时间:t 目标股：stock1 比对指数：stock2
    (stock1_now - stock1_open) / max(b , (a - (stock2_open - stock2_now)) >= x
         
"""


class Strategy(StrategyTemplate):
    name = 'open'

    def init(self):
        self.quotation_dict = {}

    def strategy(self, event):
        self.log.info('检查持仓')
        self.log.info(self.user.balance)
        self.log.info('\n')

    def clock(self, event):
        """在交易时间会定时推送 clock 事件
        :param event: event.data.clock_event 为 [0.5, 1, 3, 5, 15, 30, 60] 单位为分钟,  ['open', 'close'] 为开市、收市
            event.data.trading_state  bool 是否处于交易时间
        """
        if event.data.clock_event == 'open':
            # 开市了
            self.log.info('open')
        elif event.data.clock_event == 'close':
            # 收市了
            self.log.info('close')

    def backtest(self, event):
        stock_dick = event.data
        sh000001_list = stock_dick['sh000001']
        sz399001_list = stock_dick['sz399001']
        res_list = []
        codes = []
        for code, stock1_list in stock_dick.items():
            if code == 'sh000001' or code == 'sz399001':
                continue
            i = 0
            stock1_open = stock1_list[0][0] / stock1_list[0][1] - 1
            stock2_list = sh000001_list if code.find(
                'sh') > 0 else sz399001_list
            stock2_open = stock2_list[0][0] / stock2_list[0][1] - 1
            stock1_close = stock1_list[-1][2] / stock1_list[-1][1] - 1
            stock1_high = stock1_list[-1][3] / stock1_list[-1][1] - 1
            stock1_low = stock1_list[-1][4] / stock1_list[-1][1] - 1
            for stock1 in stock1_list:
                stock2 = stock2_list[i]
                timestamp = stock1[-1]
                sec = timestamp % 86400
                if sec >= 5400 + 300:
                    continue
                stock1_now = stock1[2] / stock1[1] - 1
                stock2_now = stock2[2] / stock2[1] - 1
                for t in range(3, 61, 3):
                    if t >= sec - 5400:
                        for a10 in range(5, 21, 1):
                            a = a10 / 10.0
                            for b10 in range(1, 5, 1):
                                b = b10 / 10.0
                                res_list.append([
                                    stock1_now, stock1_open, stock1_close, 1 - (stock1_now - stock1_low)/(stock1_high - stock1_low), stock2_now, t, a, b, (stock1_now - stock1_open) / max(
                                        b, (a - (stock2_open - stock2_now)))
                                ])
                                codes.append(code)
                        break
                i = i+1
        print("cal score finish")
        t_score = {}
        for t in range(3, 61, 3):
            s = 0.0
            c = 0
            for res in res_list:
                if res[5] == t:
                    s += res[3]
                    c += 1
            if c > 0:
                t_score[t] = s / c
        print(t_score)
        
        a_score = {}
        for a10 in range(5, 21, 1):
            s = 0.0
            c = 0
            for res in res_list:
                if abs(res[6] - a10 / 10) < 1e-8:
                    s += res[3]
                    c += 1
            if c > 0:
                a_score[a10/10] = s / c
        print(a_score)

        b_score = {}
        for b10 in range(1, 5, 1):
            s = 0.0
            c = 0
            for res in res_list:
                if abs(res[7] - b10 / 10) < 1e-8:
                    s += res[3]
                    c += 1
            if c > 0:
                b_score[b10/10] = s / c
        print(b_score)
    
                    
        df = pd.DataFrame(np.array(res_list), index=codes)
        df.to_excel('open.xlsx')
        print("backtest finish")
