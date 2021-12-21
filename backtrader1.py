import backtrader as bt
import pandas as pd
import json
import os

from pandas.core.frame import DataFrame

script_dir = os.path.dirname(__file__)
file_path = os.path.join(script_dir, '20211210.json')
# formatedData = []
# RVals = []

with open(file_path) as fp:
  data = json.load(fp)
  """ for index in range(len(data)):
    RVals.append(data[index]['high'] - data[index]['low'])
    if index % 3 == 0 and index + 2 < len(data):
      firstData = data[index]
      secondData = data[index + 1]
      thirdData = data[index + 2]
      low = min(firstData['low'], secondData['low'], thirdData['low'])
      high = max(firstData['high'], secondData['high'], thirdData['high'])
      volume = sum([firstData['volume'], secondData['volume'], thirdData['volume']])
      open = firstData['open']
      close = thirdData['close']
      formatedData.append({
        'timestamp': firstData['timestamp'],
        'low': low,
        'high': high,
        'open': open,
        'close': close,
        'volume': volume
      }) """

df = pd.DataFrame(data, columns=['timestamp', 'low', 'high', 'open', 'close', 'volume'])
df['date'] = pd.to_datetime(df['timestamp'])
df = df.set_index('date')

# print(df);

class PrintClose(bt.Strategy):
  def __init__(self):
    #引用data[0]中的收盘价格数据
    self.dataclose = self.datas[0].close

  def log(self, txt):     
    dt = self.datas[0].datetime
    # print(self.datas[0].datetime.date(2));  
    print('%s %s, %s' % (dt.date(0), dt.time(0), txt))
    # 打印日期和收盘价格

  def next(self):     
    #将收盘价保留两位小数再输出
    self.log('Close: %.2f' % self.dataclose[0])

if __name__ == '__main__':
  cerebro = bt.Cerebro()

  btData = bt.feeds.PandasData(dataname = df)

  cerebro.adddata(btData)
  # 设置投资金额100000.0
  cerebro.broker.setcash(100000.0)

  #给Cebro引擎添加策略
  cerebro.addstrategy(PrintClose)

  # print('组合期初资金: %.2f' % cerebro.broker.getvalue())
  cerebro.run()
  # 引擎运行后打期末资金
  # print('组合期末资金: %.2f' % cerebro.broker.getvalue())

  #运行Cebro引擎
  cerebro.run()

  # matplot 版本问题 see:https://stackoverflow.com/questions/63471764/importerror-cannot-import-name-warnings-from-matplotlib-dates
  cerebro.plot()
