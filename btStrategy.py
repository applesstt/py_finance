import backtrader as bt
# import datetime

# 待实现功能
# 1. 记录当前仓位
# 2. 在最后一根蜡烛图 强行平仓
# 3. 打印最终收益
# 4. 唐安奇通道
# 5. 计算ART
# 6. 小时级别数据 1-2年
# 7. 确认一下开仓点是否是蜡烛图的open
# 8. 引入杠杆概念
# 9. 抽象python函数

# 待实现策略
# 1. 小级别的海龟策略（与大趋势一致）
# 2. 大趋势向下 回弹但未超出前高 并连续两根未超出前高 开空 （反之同理）
# 3. 均线较差开仓 回调至前两根的高（低）点止损
class MoeStrategy(bt.Strategy): 
  #移动平均参数
  params = (('pfast',80),('pslow',300),)
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

    # 获取当前买入信号和卖出信号
    buy_signal = self.fast_sma[0] > self.slow_sma[0] and self.fast_sma[-1] < self.slow_sma[-1]
    sell_signal = self.fast_sma[0] < self.slow_sma[0] and self.fast_sma[-1] > self.slow_sma[-1]
    
    # 根据当前持仓状态决定可以执行的操作
    if not self.position:  # 没有持仓
        # 可以根据信号自由开仓
        if buy_signal:
            self.log('BUY CREATE, %.2f' % self.dataclose[0])
            self.order = self.buy()
        elif sell_signal:
            self.log('SELL CREATE, %.2f' % self.dataclose[0])
            self.order = self.sell()
    elif self.position.size > 0:  # 有多头持仓(买入)
        # 只能卖出平仓，不能继续买入
        if sell_signal:
            self.log('CLOSE LONG POSITION, %.2f' % self.dataclose[0])
            self.order = self.close()  # 平仓当前持仓
    elif self.position.size < 0:  # 有空头持仓(卖出)
        # 只能买入平仓，不能继续卖出
        if buy_signal:
            self.log('CLOSE SHORT POSITION, %.2f' % self.dataclose[0])
            self.order = self.close()  # 平仓当前持仓

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
