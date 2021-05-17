import importlib
import os
import pathlib
import signal
import sys
import threading
import time
from collections import OrderedDict
from threading import Thread, Lock

import easytrader
from logbook import Logger, StreamHandler

from .event_engine import EventEngine
from .log_handler.default_handler import DefaultLogHandler
from .push_engine.clock_engine import ClockEngine
from .push_engine.quotation_engine import DefaultQuotationEngine

log = Logger(os.path.basename(__file__))
StreamHandler(sys.stdout).push_application()

PY_MAJOR_VERSION, PY_MINOR_VERSION = sys.version_info[:2]
if (PY_MAJOR_VERSION, PY_MINOR_VERSION) < (3, 5):
    raise Exception('Python 版本需要 3.5 或以上, 当前版本为 %s.%s 请升级 Python' % (PY_MAJOR_VERSION, PY_MINOR_VERSION))

ACCOUNT_OBJECT_FILE = 'account.session'


class MainEngine:
    """主引擎，负责行情 / 事件驱动引擎 / 交易"""

    def __init__(self, broker=None, need_data=None, quotation_engines=None,
                 log_handler=DefaultLogHandler(), tzinfo=None, strategy_list=[]):
        """初始化事件 / 行情 引擎并启动事件引擎
        """
        self.log = log_handler
        self.broker = broker

        # 登录账户
        if (broker is not None) and (need_data is not None):
            self.user = easytrader.use(broker)
            need_data_file = pathlib.Path(need_data)
            if need_data_file.exists():
                self.user.prepare(need_data)
            else:
                log_handler.warn("券商账号信息文件 %s 不存在, easytrader 将不可用" % need_data)
        else:
            self.user = None
            self.log.info('选择了无交易模式')

        self.event_engine = EventEngine()
        self.clock_engine = ClockEngine(self.event_engine, tzinfo)

        quotation_engines = quotation_engines or [DefaultQuotationEngine]

        if type(quotation_engines) != list:
            quotation_engines = [quotation_engines]
        else:
            types = [quo.EventType for quo in quotation_engines]
            if len(types) != len(set(types)):
                types.sort()
                types = ','.join([str(t) for t in types])
                raise ValueError("行情引擎 EventType 重复:" + types)
        self.quotation_engines = []
        for quotation_engine in quotation_engines:
            self.quotation_engines.append(quotation_engine(self.event_engine, self.clock_engine))

        # 修改时间缓存
        self._cache = {}
        # 文件模块映射
        self._modules = {}
        self._names = None

        # shutdown 函数
        self.before_shutdown = []  # 关闭引擎前的 shutdown
        self.main_shutdown = []  # 引擎自身要执行的 shutdown
        self.after_shutdown = []  # 关闭引擎后的 shutdown
        self.shutdown_signals = [
            signal.SIGINT,  # 键盘信号
            signal.SIGTERM,  # kill 命令
        ]
        if sys.platform != 'win32':
            self.shutdown_signals.extend([signal.SIGHUP, signal.SIGQUIT])

        for s in self.shutdown_signals:
            # 捕获退出信号后的要调用的,唯一的 shutdown 接口
            signal.signal(s, self._shutdown)

        self.strategy_list = []
        for strategy in strategy_list:
            self.strategy_list.append(strategy(self.user,self.log,self))
            
        self.log.info('启动主引擎')

    def start(self):
        """启动主引擎"""
        self.event_engine.start()
        self._add_main_shutdown(self.event_engine.stop)

        if self.broker == 'gf':
            self.log.warn("sleep 10s 等待 gf 账户加载")
            time.sleep(10)
        for quotation_engine in self.quotation_engines:
            quotation_engine.start()
            self._add_main_shutdown(quotation_engine.stop)

        self.clock_engine.start()
        self._add_main_shutdown(self.clock_engine.stop)

    def strategy_listen_event(self, strategy, _type="listen"):
        """
        所有策略要监听的事件都绑定到这里
        :param strategy: Strategy()
        :param _type: "listen" OR "unlisten"
        :return:
        """
        func = {
            "listen": self.event_engine.register,
            "unlisten": self.event_engine.unregister,
        }.get(_type)

        # 行情引擎的事件
        for quotation_engine in self.quotation_engines:
            func(quotation_engine.EventType, strategy.run)

        # 时钟事件
        func(ClockEngine.EventType, strategy.clock)

    def get_strategy(self, name):
        for strategy in self.strategy_list:
            if strategy.name == name:
                return strategy
        return None

    def get_quotation(self, eventype):
        for quo in self.quotation_engines:
            if quo.EventType == eventype:
                return quo
        else:
            return None

    def add_before_shutdown(self, shutdown):

        if not hasattr(shutdown, "__call__"):
            n = shutdown.__name__ if hasattr(shutdown, "__name__") else str(shutdown)
            raise ValueError("%s 不是可调用对象 " % n)

        self.before_shutdown.append(shutdown)

    def add_after_shutdown(self, shutdown):
        if not hasattr(shutdown, "__call__"):
            n = shutdown.__name__ if hasattr(shutdown, "__name__") else str(shutdown)
            raise ValueError("%s 不是可调用对象 " % n)

        self.after_shutdown.append(shutdown)

    def _add_main_shutdown(self, shutdown):
        if not hasattr(shutdown, "__call__"):
            n = shutdown.__name__ if hasattr(shutdown, "__name__") else str(shutdown)
            raise ValueError("%s 不是可调用对象 " % n)

        self.main_shutdown.append(shutdown)

    def _shutdown(self, sig, frame):
        """
        关闭进程前的处理
        :return:
        """
        self.log.debug("开始关闭进程...")
        # 所有 shutdown 前的触发点
        for st in self.before_shutdown:
            st()

        # 引擎自身的 shutdown
        for st in self.main_shutdown:
            st()

        # 等待所有线程关闭, 直到只留下主线程
        c = threading.active_count()
        while threading.active_count() != c:
            time.sleep(2)

        # 调用策略的 shutdown
        self.log.debug("开始关闭策略...")
        for s in self.strategy_list:
            s.shutdown()

        # 所有 shutdown 后的触发点
        for st in self.after_shutdown:
            st()

        # 退出
        time.sleep(.1)
        sys.exit(1)
