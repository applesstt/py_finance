from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Common")

from System import *
from QuantConnect import *
from QuantConnect.Algorithm import *
from QuantConnect.Data import *
from QuantConnect.Securities import *
from QuantConnect.Securities.Option import *
from datetime import timedelta
import numpy as np

class SPY0DTEOptionStrategy(QCAlgorithm):
    
    def Initialize(self):
        # 设置回测的开始日期和现金
        self.SetStartDate(2024, 1, 20)
        self.SetEndDate(2024, 2, 20)
        self.SetCash(10000)  # 初始资金
        
        # 设置数据分辨率和数据订阅
        self.SetTimeZone("America/New_York")
        equity = self.AddEquity("SPY", Resolution.Minute)
        self.spy = equity.Symbol
        
        # 添加SPY期权
        option = self.AddOption("SPY", Resolution.Minute)
        option.SetFilter(lambda universe: universe.IncludeWeeklys()
                                               .Strikes(-5, 5)
                                               .Expiration(0, 1))
        
        # 初始化变量
        self.dayBarCount = 0  # 当日K线计数
        self.dayHigh = 0      # 当日最高价
        self.dayLow = float('inf')  # 当日最低价
        self.newUpCount = 0   # 最高价不变计数
        self.newDownCount = 0 # 最低价不变计数
        self.previousDayHigh = 0  # 前一个最高价
        self.previousDayLow = float('inf')  # 前一个最低价
        
        # 交易状态变量
        self.inLongPosition = False
        self.inShortPosition = False
        self.entryPrice = 0
        self.entryTime = None
        self.highestSinceEntry = 0
        self.lowestSinceEntry = float('inf')
        
        # KDJ 参数
        self.n1 = 18
        self.m1 = 18
        self.m2 = 4
        self.kdj_history = []  # 存储KDJ值的历史
        
        # 价格通道线
        self.dd0, self.dd1, self.dd2, self.dd3, self.dd4, self.dd5, self.dd6 = [0] * 7
        self.uu0, self.uu1, self.uu2, self.uu3, self.uu4, self.uu5, self.uu6 = [0] * 7
        
        # 新价格通道
        self.ddo_new1, self.dd1_new1, self.dd2_new1, self.dd3_new1 = [0] * 4
        self.dd4_new1, self.dd5_new1, self.dd6_new1, self.dd7_new1, self.dd8_new1 = [0] * 5
        self.uuo_new1, self.uu1_new1, self.uu2_new1, self.uu3_new1 = [0] * 4
        self.uu4_new1, self.uu5_new1, self.uu6_new1, self.uu7_new1, self.uu8_new1 = [0] * 5
        
        # 存储价格数据的历史
        self.price_history = []
        
        # 记录上次交易的信号类型和时间，用于信号过滤
        self.lastSignalType = None
        self.lastSignalTime = None
        
        # 交易时间限制 - 多窗口设置
        self.market_open_time = None
        
        # 获取参数并确保转换为整数
        try:
            start_min = int(self.get_parameter('start_min'))
            end_min = int(self.get_parameter('end_min'))
        except (ValueError, TypeError):
            # 如果参数不是有效的整数或者参数不存在，使用默认值
            self.Debug("无法获取有效的start_min或end_min参数，使用默认值")
            start_min = 15
            end_min = 70
            
        # 定义多个交易窗口，格式为 [{"start": 开始分钟, "end": 结束分钟}, ...]
        self.trading_windows = [
            {"start": start_min, "end": end_min},
            # {"start": 180, "end": 210}, 
            # {"start": 360, "end": 390} 
        ]
        
        # 设置每天开盘时重置
        self.Schedule.On(self.DateRules.EveryDay(self.spy), 
                         self.TimeRules.AfterMarketOpen(self.spy, 1), 
                         self.ResetDailyValues)
        
        # 设置收盘前平仓
        self.Schedule.On(self.DateRules.EveryDay(self.spy), 
                         self.TimeRules.BeforeMarketClose(self.spy, 10), 
                         self.CloseAllPositions)
        
        self.Debug(f"回测设置的开始日期: {self.StartDate}")
        self.Debug(f"回测设置的结束日期: {self.EndDate}")
        self.Debug(f"交易窗口设置: {len(self.trading_windows)}个交易时段")
        for i, window in enumerate(self.trading_windows):
            self.Debug(f"窗口 {i+1}: 开盘后{window['start']}分钟 至 开盘后{window['end']}分钟")
        
        self.settings.daily_precise_end_time = False
        
        # 在Initialize中设置
        self.price_channel_step = 1.2  # 价格通道步长
    
    def ResetDailyValues(self):
        """每日开盘重置值"""
        self.dayBarCount = 0
        self.dayHigh = 0
        self.dayLow = float('inf')
        self.newUpCount = 0
        self.newDownCount = 0
        self.previousDayHigh = 0
        self.previousDayLow = float('inf')
        self.price_history = []
        self.kdj_history = []
        
        # 记录每日开盘时间，用于计算交易窗口
        self.market_open_time = self.Time
        self.Debug(f"=== 新交易日开始: {self.Time.date()} ===")
        
        # 输出每个交易窗口的具体时间
        for i, window in enumerate(self.trading_windows):
            # 确保start和end是整数类型
            start_min = int(window["start"]) if isinstance(window["start"], str) else window["start"]
            end_min = int(window["end"]) if isinstance(window["end"], str) else window["end"]
            
            window_start = self.market_open_time + timedelta(minutes=start_min)
            window_end = self.market_open_time + timedelta(minutes=end_min)
            self.Debug(f"交易窗口 {i+1}: {window_start.time()} 至 {window_end.time()}")
    
    def OnData(self, data):
        """每个数据事件处理"""
        if not data.ContainsKey(self.spy) or not data[self.spy]:
            return
        
        # 更新K线计数和价格历史
        self.dayBarCount += 1
        current_price = data[self.spy].Close
        current_high = data[self.spy].High
        current_low = data[self.spy].Low
        
        # 更新价格历史
        self.price_history.append({
            'time': self.Time,
            'open': data[self.spy].Open,
            'high': current_high,
            'low': current_low,
            'close': current_price
        })
        
        # 更新当日最高最低价
        if current_high > self.dayHigh:
            self.previousDayHigh = self.dayHigh
            self.dayHigh = current_high
            self.newUpCount = 0
        else:
            self.newUpCount += 1
            
        if current_low < self.dayLow:
            self.previousDayLow = self.dayLow
            self.dayLow = current_low
            self.newDownCount = 0
        else:
            self.newDownCount += 1
        
        # 计算交易条件
        self.CalculateConditions()
        
        # 计算KDJ指标
        self.CalculateKDJ()
        
        # 根据持仓状态和信号生成交易
        self.GenerateTradeSignals()
        
        # 更新持仓中的最高/最低价
        if self.inLongPosition:
            if current_price > self.highestSinceEntry:
                self.highestSinceEntry = current_price
                self.Debug(f"更新多头持仓最高价: {self.highestSinceEntry}")
                
        if self.inShortPosition:
            if current_low < self.lowestSinceEntry:
                self.lowestSinceEntry = current_low
                self.Debug(f"更新空头持仓最低价: {self.lowestSinceEntry}")
    
    def CalculateConditions(self):
        """计算各种交易条件"""
        # 日内K线位置条件
        self.condt1 = self.dayBarCount < 70
        self.condt2 = self.dayBarCount >= 70 and self.dayBarCount < 140
        self.condt3 = self.dayBarCount >= 140 and self.dayBarCount < 220
        self.condt4 = self.dayBarCount >= 220 and self.dayBarCount < 340
        
        # 日内价格区间
        self.dayku = self.dayHigh - self.dayLow if self.dayLow != float('inf') else 0
        self.condt0 = self.dayku <= 2.4
        
        # 价格连续性
        self.newup = self.CheckConsecutiveCondition(self.newUpCount, 69)
        self.newdown = self.CheckConsecutiveCondition(self.newDownCount, 69)
        
        # 计算价格通道
        if (self.condt1 or self.condt2) and not self.newup:
            self.dd0 = self.dayHigh
            self.dd1 = self.dd0 - self.price_channel_step
            self.dd2 = self.dd0 - 2 * self.price_channel_step
            self.dd3 = self.dd0 - 3.6
            self.dd4 = self.dd0 - 4.8
            self.dd5 = self.dd0 - 6.0
            self.dd6 = self.dd0 - 7.2
        
        if (self.condt1 or self.condt2) and not self.newdown:
            self.uu0 = self.dayLow
            self.uu1 = self.uu0 + 1.2
            self.uu2 = self.uu0 + 2.4
            self.uu3 = self.uu0 + 3.6
            self.uu4 = self.uu0 + 4.8
            self.uu5 = self.uu0 + 6.0
            self.uu6 = self.uu0 + 7.2
        
        # 计算新价格通道
        self.kuand = self.dayHigh - self.dayLow if self.dayLow != float('inf') else 0
        
        # 为了简化，暂时使用与主通道相同的值
        self.uuo_new1 = self.uu0
        self.uu1_new1 = self.uu1
        
        # 其他条件计算会在触发信号时进行
    
    def CalculateKDJ(self):
        """计算KDJ指标"""
        if len(self.price_history) < self.n1:
            return
        
        # 截取最近N1个周期的数据
        recent_data = self.price_history[-self.n1:]
        
        # 计算最低价和最高价
        low_min = min(bar['low'] for bar in recent_data)
        high_max = max(bar['high'] for bar in recent_data)
        
        # 计算RSV
        if high_max - low_min == 0:
            rsv = 50
        else:
            rsv = 100 * (recent_data[-1]['close'] - low_min) / (high_max - low_min)
        
        # 计算K值和D值
        if len(self.kdj_history) == 0:
            k = 50
            d = 50
        else:
            k = (2 * self.kdj_history[-1]['k'] + rsv) / 3
            d = (2 * self.kdj_history[-1]['d'] + k) / 3
        
        # 计算J值
        j = 3 * k - 2 * d
        
        # 存储KDJ值
        self.kdj_history.append({'k': k, 'd': d, 'j': j})
    
    def GetCurrentKDJ(self):
        """获取当前KDJ值"""
        if not self.kdj_history:
            return (50, 50, 50)
        return (self.kdj_history[-1]['k'], self.kdj_history[-1]['d'], self.kdj_history[-1]['j'])
    
    def CheckConsecutiveCondition(self, count, threshold):
        """检查N个周期内价格是否保持不变"""
        return count >= threshold  # 考虑改为69作为阈值，与原策略匹配
    
    def GenerateTradeSignals(self):
        """生成交易信号"""
        if not self.price_history or len(self.price_history) < 3:
            return
        
        current_price = self.price_history[-1]['close']
        current_high = self.price_history[-1]['high']
        current_low = self.price_history[-1]['low']
        
        # 获取KDJ值
        kn, dn, jn = self.GetCurrentKDJ()
        
        # 买入信号条件
        buy_signal = False
        # 计算买入条件1: CROSS(C,UU2)&&KUAND>2.5&&(CONDT1||CONDT2)&&CONDKJ1=0
        if (len(self.price_history) >= 2 and 
            self.price_history[-2]['close'] <= self.uu2 and 
            current_price > self.uu2 and 
            self.kuand > 2.5 and 
            (self.condt1 or self.condt2) and 
            not (jn < kn and jn > 25)):
            buy_signal = True
            self.Debug("触发买入信号1")
        
        # 计算买入条件2: CROSS(C,UU1)&&C-LLV(L,3)>1.15&&(CONDT1||CONDT2)
        if not buy_signal:
            recent_lows = [bar['low'] for bar in self.price_history[-3:]]
            if (len(self.price_history) >= 2 and 
                self.price_history[-2]['close'] <= self.uu1 and 
                current_price > self.uu1 and 
                current_price - min(recent_lows) > 1.15 and 
                (self.condt1 or self.condt2)):
                buy_signal = True
                # self.Debug("触发买入信号2")
        
        # 计算买入条件3: CROSS(C,UU1_NEW1)&&JN>KN&&DAYKU>3.5&&DAYKU<5.3
        if not buy_signal:
            if (len(self.price_history) >= 2 and 
                self.price_history[-2]['close'] <= self.uu1_new1 and 
                current_price > self.uu1_new1 and 
                jn > kn and 
                self.dayku > 3.5 and 
                self.dayku < 5.3):
                buy_signal = True
                # self.Debug("触发买入信号3")
        
        # 例如添加DAYBARPOS<46条件
        if (len(self.price_history) >= 2 and 
            self.price_history[-2]['close'] <= self.uu1 and 
            current_price > self.uu1 and 
            self.kuand > 2.5 and 
            (self.condt1 or self.condt2) and 
            not (jn < kn and jn > 25) and
            self.dayBarCount < 46):  # 添加此条件
            buy_signal = True
        
        # 卖出信号条件
        sell_signal = False
        # 计算卖出条件1: CROSSDOWN(H,DD2)&&KUAND>2.5&&(CONDT1||CONDT2)&&JN<KN
        if (len(self.price_history) >= 2 and 
            self.price_history[-2]['high'] >= self.dd2 and 
            current_high < self.dd2 and 
            self.kuand > 2.5 and 
            (self.condt1 or self.condt2) and 
            jn < kn):
            sell_signal = True
            # self.Debug("触发卖出信号1")
        
        # 计算卖出条件2: CROSSDOWN(C,DD2)&&-C+HHV(H,3)>1&&(CONDT1||CONDT2)
        if not sell_signal:
            recent_highs = [bar['high'] for bar in self.price_history[-3:]]
            if (len(self.price_history) >= 2 and 
                self.price_history[-2]['close'] >= self.dd2 and 
                current_price < self.dd2 and 
                max(recent_highs) - current_price > 1 and 
                (self.condt1 or self.condt2)):
                sell_signal = True
                # self.Debug("触发卖出信号2")
        
        # 计算卖出条件3: CROSSDOWN(C,DD1)&&EVERY(JN<15.5,DAYBARPOS)&&(CONDT1||CONDT2)
        if not sell_signal:
            all_j_below = True
            for kdj in self.kdj_history:
                if kdj['j'] >= 15.5:
                    all_j_below = False
                    break
            
            if (len(self.price_history) >= 2 and 
                self.price_history[-2]['close'] >= self.dd1 and 
                current_price < self.dd1 and 
                all_j_below and 
                (self.condt1 or self.condt2)):
                sell_signal = True
                # self.Debug("触发卖出信号3")
        
        # 平仓信号检查 - 多头平仓
        if self.inLongPosition:
            # 止盈条件1: C-BKPRICE>2.4&&C-REF(C,3)<0.74
            if (current_price - self.entryPrice > 2.4 and 
                len(self.price_history) >= 4 and 
                current_price - self.price_history[-4]['close'] < 0.74):
                self.ClosePosition("多头止盈信号1")
                return
            
            # 止盈条件2: C-BKPRICE>2.2&&BARSBK<=24
            if (current_price - self.entryPrice > 2.2 and 
                (self.Time - self.entryTime).total_seconds() / 60 <= 24):
                self.ClosePosition("多头止盈信号2")
                return
            
            # 止盈条件3: C>UU4
            if current_price > self.uu4:
                self.ClosePosition("多头止盈信号3")
                return
            
            # 回撤止盈: 从最高点回撤超过5%
            if self.highestSinceEntry > 0:
                retracement = (self.highestSinceEntry - current_price) / self.highestSinceEntry
                if retracement > 0.05:  # 5%回撤
                    self.ClosePosition(f"多头回撤平仓: {retracement*100:.2f}%")
                    return
            
            # 止损条件: C-BKPRICE<-1.3
            if current_price - self.entryPrice < -1.3:
                self.ClosePosition("多头止损信号")
                return
        
        # 平仓信号检查 - 空头平仓
        if self.inShortPosition:
            # 止盈条件1: SKPRICE-C>3.3&&REF(C,3)-C<0.74
            if (self.entryPrice - current_price > 3.3 and 
                len(self.price_history) >= 4 and 
                self.price_history[-4]['close'] - current_price < 0.74):
                self.ClosePosition("空头止盈信号1")
                return
            
            # 止损条件: SKPRICE-C<-1.45
            if self.entryPrice - current_price < -1.45:
                self.ClosePosition("空头止损信号")
                return
            
            # 回撤止盈: 从最低点反弹超过5%
            if self.lowestSinceEntry < float('inf'):
                retracement = (current_price - self.lowestSinceEntry) / self.lowestSinceEntry
                if retracement > 0.05:  # 5%回撤
                    self.ClosePosition(f"空头回撤平仓: {retracement*100:.2f}%")
                    return
            
            # KDJ平仓条件
            if current_low < self.dd3 and jn > kn:
                self.ClosePosition("空头KDJ平仓信号1")
                return
            
            if current_low < self.dd5:
                self.ClosePosition("空头止盈信号2")
                return
        
        # 执行交易
        if not self.inLongPosition and not self.inShortPosition:
            # 只在开盘后15分钟内开仓
            if not self.IsWithinTradingWindow():
                if buy_signal or sell_signal:
                    self.Debug(f"触发交易信号，但不在交易窗口内 (当前时间: {self.Time})")
                return
                
            if buy_signal and self.IsValidSignal("BK"):
                self.EnterLong()
            elif sell_signal and self.IsValidSignal("SK"):
                self.EnterShort()
    
    def IsValidSignal(self, signal_type):
        """根据自动过滤规则验证信号"""
        # 如果没有上一个信号，所有信号都有效
        if self.lastSignalType is None:
            return True
        
        # BK后只能有SP
        if self.lastSignalType == "BK" and signal_type != "SP":
            return False
        
        # SK后只能有BP
        if self.lastSignalType == "SK" and signal_type != "BP":
            return False
        
        # 两分钟内不重复交易
        if self.lastSignalTime is not None:
            time_diff = (self.Time - self.lastSignalTime).total_seconds() / 60
            if time_diff < 2:
                return False
        
        return True
    
    def EnterLong(self):
        """买入开仓"""
        if self.inLongPosition or self.inShortPosition:
            return
            
        # 再次检查是否在交易窗口内
        if not self.IsWithinTradingWindow():
            self.Debug("尝试多头开仓，但已超出交易窗口期")
            return
        
        # 获取合适的期权合约
        contracts = self.GetOptionContracts(True)  # 买入看涨期权
        if not contracts:
            self.Debug("找不到合适的看涨期权合约")
            return
        
        # 使用第一个符合条件的合约
        contract = contracts[0]
        quantity = self.CalculatePositionSize(contract.Price)
        
        # 执行买入
        self.Buy(contract.Symbol, quantity)
        self.Debug(f"买入开仓: {contract.Symbol.Value}, 价格: {contract.Price}, 数量: {quantity}")
        
        # 更新状态
        self.inLongPosition = True
        self.entryPrice = self.Securities[self.spy].Price
        self.entryTime = self.Time
        self.highestSinceEntry = self.entryPrice
        self.lastSignalType = "BK"
        self.lastSignalTime = self.Time
    
    def EnterShort(self):
        """卖出开仓"""
        if self.inLongPosition or self.inShortPosition:
            return
            
        # 再次检查是否在交易窗口内
        if not self.IsWithinTradingWindow():
            self.Debug("尝试空头开仓，但已超出交易窗口期")
            return
        
        # 获取合适的期权合约
        contracts = self.GetOptionContracts(False)  # 买入看跌期权
        if not contracts:
            self.Debug("找不到合适的看跌期权合约")
            return
        
        # 使用第一个符合条件的合约
        contract = contracts[0]
        quantity = self.CalculatePositionSize(contract.Price)
        
        # 执行买入
        self.Buy(contract.Symbol, quantity)
        self.Debug(f"卖出开仓(买入看跌期权): {contract.Symbol.Value}, 价格: {contract.Price}, 数量: {quantity}")
        
        # 更新状态
        self.inShortPosition = True
        self.entryPrice = self.Securities[self.spy].Price
        self.entryTime = self.Time
        self.lowestSinceEntry = self.entryPrice
        self.lastSignalType = "SK"
        self.lastSignalTime = self.Time
    
    def ClosePosition(self, reason=""):
        """平仓当前持仓"""
        # 获取持仓
        holdings = list(self.Portfolio.Values)
        closed = False
        
        for holding in holdings:
            if holding.Invested:
                self.Liquidate(holding.Symbol)
                self.Debug(f"平仓 {holding.Symbol.Value}: {reason}")
                closed = True
        
        if closed:
            # 重置状态
            self.inLongPosition = False
            self.inShortPosition = False
            self.lastSignalType = "SP" if self.inLongPosition else "BP"
            self.lastSignalTime = self.Time
    
    def CloseAllPositions(self):
        """收盘前关闭所有持仓"""
        self.Liquidate()
        self.inLongPosition = False
        self.inShortPosition = False
        self.Debug("收盘前平仓所有持仓")
    
    def GetOptionContracts(self, is_call):
        """获取符合条件的期权合约"""
        contracts = []
        
        # 获取当前可用的期权合约
        option_chain = self.OptionChainProvider.GetOptionContractList(self.spy, self.Time)
        
        # 获取当天日期
        today = self.Time.date()
        
        # 筛选期权合约
        for symbol in option_chain:
            # 验证是当天到期的合约
            if symbol.ID.Date.date() == today:
                # 验证是看涨(Call)还是看跌(Put)期权
                if (is_call and symbol.ID.OptionRight == OptionRight.Call) or \
                   (not is_call and symbol.ID.OptionRight == OptionRight.Put):
                    
                    # 检查合约是否在我们的证券集合中并且价格在指定范围内
                    if symbol in self.Securities.Keys:
                        option = self.Securities[symbol]
                        price = option.Price
                        
                        # 筛选价格范围在 0.65-1.35 之间的合约
                        if 0.65 <= price <= 1.35:
                            contracts.append(option)
        
        # 如果没有找到合约，尝试宽松价格限制
        if not contracts:
            self.Debug("指定价格范围内没有找到合约，扩大搜索范围")
            for symbol in option_chain:
                if symbol.ID.Date.date() == today:
                    if (is_call and symbol.ID.OptionRight == OptionRight.Call) or \
                       (not is_call and symbol.ID.OptionRight == OptionRight.Put):
                        if symbol in self.Securities.Keys:
                            option = self.Securities[symbol]
                            contracts.append(option)
        
        # 按价格排序（从低到高）
        return sorted(contracts, key=lambda x: x.Price) if contracts else []
    
    def CalculatePositionSize(self, option_price):
        """计算期权头寸大小"""
        # 使用总资金的5%用于每次交易
        risk_amount = self.Portfolio.Cash * 0.05
        
        # 计算可以购买的合约数量
        contracts = int(risk_amount / (option_price * 100))  # 期权1张控制100股
        
        # 确保至少购买1张合约
        return max(1, contracts)

    # 计算CONDKRUO
    def CalculateCONDKRUO(self):
        jn_crosses_down_kn_count = 0
        jn_above_kn_count = 0
        kn_above_jn_count = 0
        
        for i in range(len(self.kdj_history)-1):
            if self.kdj_history[i]['j'] > self.kdj_history[i]['k'] and self.kdj_history[i+1]['j'] <= self.kdj_history[i+1]['k']:
                jn_crosses_down_kn_count += 1
            
            if self.kdj_history[i]['j'] > self.kdj_history[i]['k']:
                jn_above_kn_count += 1
            else:
                kn_above_jn_count += 1
        
        condkruo = jn_crosses_down_kn_count <= 1 and jn_above_kn_count > kn_above_jn_count

    def IsWithinTradingWindow(self):
        """检查当前时间是否在任一交易窗口内"""
        if self.market_open_time is None:
            return False
            
        # 计算当前时间与开盘时间的差异（分钟）
        time_since_open = (self.Time - self.market_open_time).total_seconds() / 60
        
        # 检查当前时间是否在任意一个交易窗口内
        for window in self.trading_windows:
            # 确保start和end是整数类型
            start_min = int(window["start"]) if isinstance(window["start"], str) else window["start"]
            end_min = int(window["end"]) if isinstance(window["end"], str) else window["end"]
            
            if start_min <= time_since_open <= end_min:
                return True
                
        return False