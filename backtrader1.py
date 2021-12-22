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

class MAcrossover(bt.Strategy): 
  #移动平均参数
  params = (('pfast',5),('pslow',15),)
  def log(self, txt, dt=None):     
    dt = dt or self.datas[0].datetime.date(0)     
    print('%s, %s' % (dt.isoformat(), txt))  # 执行策略优化时 可注释掉此行
  def __init__(self):     
    self.dataclose = self.datas[0].close     
    # Order变量包含持仓数据与状态
    self.order = None     
    # 初始化移动平均数据     
    self.slow_sma = bt.indicators.MovingAverageSimple(self.datas[0], period=self.params.pslow)     
    self.fast_sma = bt.indicators.MovingAverageSimple(self.datas[0], period=self.params.pfast)
  def notify_order(self, order):
    if order.status in [order.Submitted, order.Accepted]:
      #主动买卖的订单提交或接受时  - 不触发
      return
    #验证订单是否完成
    #注意: 当现金不足时，券商可以拒绝订单
    if order.status in [order.Completed]:
      if order.isbuy():             
        self.log('BUY EXECUTED, %.2f' % order.executed.price)         
      elif order.issell():             
        self.log('SELL EXECUTED, %.2f' % order.executed.price)
      self.bar_executed = len(self)
    elif order.status in [order.Canceled, order.Margin, order.Rejected]:
      self.log('Order Canceled/Margin/Rejected')     
    #重置订单
    self.order = None
  def next(self):
    # 检测是否有未完成订单
    if self.order:
      return
    #验证是否有持仓
    if not self.position:
    #如果没有持仓，寻找开仓信号
      #SMA快线突破SMA慢线
      if self.fast_sma[0] > self.slow_sma[0] and self.fast_sma[-1] < self.slow_sma[-1]:
        self.order = self.buy()
      #如果SMA快线跌破SMA慢线
      elif self.fast_sma[0] < self.slow_sma[0] and self.fast_sma[-1] > self.slow_sma[-1]:
        self.log('SELL CREATE, %.2f' % self.dataclose[0])
        #继续追踪已经创建的订单，避免重复开仓
        self.order = self.sell()
    else:
      # 如果已有持仓，寻找平仓信号
      if len(self) >= (self.bar_executed + 5):
        self.log('CLOSE CREATE, %.2f' % self.dataclose[0])
        self.order = self.close()


""" class PrintClose(bt.Strategy):
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
    self.log('Close: %.2f' % self.dataclose[0]) """

if __name__ == '__main__':
  cerebro = bt.Cerebro()

  btData = bt.feeds.PandasData(dataname = df)

  cerebro.adddata(btData)
  # 设置投资金额100000.0
  cerebro.broker.setcash(100000.0)

  #给Cebro引擎添加策略
  cerebro.addstrategy(MAcrossover)

  # print('组合期初资金: %.2f' % cerebro.broker.getvalue())
  # 引擎运行后打期末资金
  # print('组合期末资金: %.2f' % cerebro.broker.getvalue())

  #运行Cebro引擎
  cerebro.run()

  # matplot 版本问题 see:https://stackoverflow.com/questions/63471764/importerror-cannot-import-name-warnings-from-matplotlib-dates
  cerebro.plot()
