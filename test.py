import easyquotation

import easyquant
from easyquant import DefaultQuotationEngine, DefaultLogHandler, PushBaseEngine
from easyquant import RedisIo
from custom.fixeddataengine import FixedDataEngine
from custom.fixedmainengine import FixedMainEngine
from strategies.open_strategy import OpenStrategy
from strategies.save import SaveStrategy


#choose = input('1: 华泰 2: 佣金宝 3: 银河 4: 雪球模拟组合 5: 广发\n:')
choose = '4'
broker = 'ht'
if choose == '2':
    broker = 'yjb'
elif choose == '3':
    broker = 'yh'
elif choose == '4':
    broker = 'xq'
elif choose == '5':
    broker = 'gf'


def get_broker_need_data(choose_broker):
    need_data = input('请输入你的帐号配置文件路径(直接回车使用 %s.json)\n:' % choose_broker)
    if need_data == '':
        return '%s.json' % choose_broker
    return need_data


need_data = 'xq.json'

#quotation_choose = input('请输入使用行情引擎 1: sina 2: leverfun 十档 行情(目前只选择了 162411, 000002)\n:')
quotation_choose = '1'
quotation_engine = FixedDataEngine
quotation_engine.PushInterval = 1
# quotation_engine.Backtest = True
log_type = 'file'

log_filepath = './logs'

log_handler = DefaultLogHandler(name='测试', log_type=log_type, filepath=log_filepath)

m = FixedMainEngine(None ,[OpenStrategy] ,None, quotation_engines=[quotation_engine], log_handler=log_handler,ext_stocks=["sz000002","sh600338","sz002230","sh601669","sz000002","sz000625","sh600635","sh601229","sz000799","sh600380",'sh603778','sh600531','sh601949','sh600085','sz000650','sz002626','sh000001','sz399001'])
m.start()
