import time
from datetime import date
import datetime as dt
from dateutil import tz
from easyquant import DefaultLogHandler
from easyquant import StrategyTemplate
import numpy as np
import os
class Strategy(StrategyTemplate):
    name = 'save'
    
    def init(self):
        t = date.today().isoformat()
        self.dir = './data/{}'.format(t)
        if not os.path.exists(self.dir):
            os.mkdir(self.dir)
        self.clock_engine.register_interval(1.5, trading=False)
        self.quotation_dict = {}

    def strategy(self, event):
        print(time.time())
        print(len(event.data))
        for code,quotation in  event.data.items():
            np_list=self.quotation_dict.get(code,None)
            arr = []
            for k,v in quotation.items():
                if isinstance(v, (int,float)):
                    arr.append(v)
            s = '{} {}'.format(quotation['date'],quotation['time'])
            t = time.strptime(s, '%Y-%m-%d %H:%M:%S')
            arr.append(time.mktime(t))
            if np_list is None:
                self.quotation_dict[code] = np.array(arr)
            else:
                last_np = np_list
                if not isinstance(np_list[-1], (int,float)) :
                    last_np = np_list[-1] 
                if last_np[7] != arr[7]:
                    self.quotation_dict[code] = np.vstack((np_list,np.array(arr)))

    def clock(self, event):
        if event.data.clock_event == 1.5:
            for k,v in self.quotation_dict.items():
                np.save(os.path.join(self.dir,k),v)

    def shutdown(self):
        for k,v in self.quotation_dict.items():
            np.save('./data/{}/{}'.format(date.today().isoformat(),k),v)
