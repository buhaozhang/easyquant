# !/usr/bin/python
# vim: set fileencoding=utf8 :
#
__author__ = 'keping.chu'

import importlib
import os
from threading import Thread, Lock

import time
from easyquant.log_handler.default_handler import DefaultLogHandler
from easyquant.main_engine import MainEngine
from easyquant.multiprocess.strategy_wrapper import ProcessWrapper
from easyquant.push_engine.clock_engine import ClockEngine
from .fixeddataengine import FixedDataEngine


class FixedMainEngine(MainEngine):
    def __init__(self, broker,strategy_list, need_data='ht.json', quotation_engines=[FixedDataEngine],
                 log_handler=DefaultLogHandler(), ext_stocks=[]):
        super(FixedMainEngine, self).__init__(broker, need_data, [], log_handler,strategy_list=strategy_list)
        if type(quotation_engines) != list:
            quotation_engines = [quotation_engines]
        self.quotation_engines = []
        # 修改时间缓存
        self._cache = {}
        # 文件模块映射
        self._modules = {}
        self._names = None
        # 加载锁
        self.lock = Lock()
        for quotation_engine in quotation_engines:
            self.quotation_engines.append(quotation_engine(self.event_engine, self.clock_engine, ext_stocks))
        for strategy in self.strategy_list:
            self.bind_event(strategy)

    def bind_event(self, strategy):
        """
        绑定事件
        """
        for quotation_engine in self.quotation_engines:
            self.event_engine.register(quotation_engine.EventType, strategy.strategy)
            self.event_engine.register(quotation_engine.BacktestEventType, strategy.backtest)
        self.event_engine.register(ClockEngine.EventType, strategy.clock)

    def unbind_event(self, strategy):
        """
        移除事件
        """
        for quotation_engine in self.quotation_engines:
            self.event_engine.unregister(quotation_engine.EventType, strategy.on_event)
            self.event_engine.unregister(quotation_engine.BacktestEventType, strategy.on_backtest)
        self.event_engine.unregister(ClockEngine.EventType, strategy.on_clock)
