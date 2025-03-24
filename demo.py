import pandas as pd
import yfinance as yf
import mplfinance as mpf
import json
import os
import numpy as np
from typing import TypedDict, Dict, Any, List

# 定义JSON数据的类型结构
class TradeRecord(TypedDict):
    timestamp: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    trades: int
    volume: int
    vwap: float
    lastSize: int
    turnover: int
    homeNotional: float
    foreignNotional: int

# 定义格式化后数据的类型
class FormattedTradeData(TypedDict):
    timestamp: str
    low: float
    high: float
    open: float
    close: float
    volume: int

script_dir = os.path.dirname(__file__)
file_path = os.path.join(script_dir, 'data/20211210.json')
formatedData: "list[FormattedTradeData]" = []
RVals: "list[float]" = []

with open(file_path) as fp:
  data: "list[TradeRecord]" = json.load(fp)
  for index in range(len(data)):
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
      })

df = pd.DataFrame(formatedData, columns=['timestamp', 'low', 'high', 'open', 'close', 'volume'])
df['date'] = pd.to_datetime(df['timestamp'])
df = df.set_index('date')

# 计算移动平均线（类似于btStrategy.py中的策略）
df['fast_sma'] = df['close'].rolling(window=5).mean()  # 快速移动平均线，对应btStrategy中的pfast
df['slow_sma'] = df['close'].rolling(window=20).mean() # 慢速移动平均线，对应btStrategy中的pslow

# 标记买入和卖出信号
# 买入信号：快线上穿慢线
# 卖出信号：快线下穿慢线
buy_signals = []
sell_signals = []

# 初始化信号列表
for i in range(len(df)):
    buy_signals.append(np.nan)
    sell_signals.append(np.nan)

# 检测交叉点并标记信号
for i in range(1, len(df)):
    # 买入信号：快线上穿慢线
    if df['fast_sma'].iloc[i] > df['slow_sma'].iloc[i] and df['fast_sma'].iloc[i-1] <= df['slow_sma'].iloc[i-1]:
        buy_signals[i] = df['low'].iloc[i] * 0.99  # 在K线下方略低位置标记买入信号
    
    # 卖出信号：快线下穿慢线
    if df['fast_sma'].iloc[i] < df['slow_sma'].iloc[i] and df['fast_sma'].iloc[i-1] >= df['slow_sma'].iloc[i-1]:
        sell_signals[i] = df['high'].iloc[i] * 1.01  # 在K线上方略高位置标记卖出信号

# 将信号添加到DataFrame
df['buy_signal'] = buy_signals
df['sell_signal'] = sell_signals

# 创建标记
buy_markers = mpf.make_addplot(df['buy_signal'], type='scatter', markersize=100, marker='^', color='g')
sell_markers = mpf.make_addplot(df['sell_signal'], type='scatter', markersize=100, marker='v', color='r')
fast_sma = mpf.make_addplot(df['fast_sma'], color='orange')
slow_sma = mpf.make_addplot(df['slow_sma'], color='blue')

# 计算R值
R = round(sum(RVals) / len(RVals))

# 生成图表，添加买卖标记和价格文字
fig, axes = mpf.plot(
  df,
  title='BitMex UBT 15m 2012-12-10 R:' + str(R),
  type='candle',
  style='charles',
  addplot=[fast_sma, slow_sma, buy_markers, sell_markers],
  volume=True,
  figsize=(12, 8),
  returnfig=True  # 返回图表对象，以便添加注释
)

# 获取主K线图轴对象
ax1 = axes[0]

# 为买入和卖出信号添加价格标注
for i in range(len(df)):
    # 买入信号价格标注
    if not np.isnan(df['buy_signal'].iloc[i]):
        price = df['close'].iloc[i]
        price_text = f'{price:.2f}'
        ax1.annotate(price_text, 
                     xy=(i, df['buy_signal'].iloc[i]),
                     xytext=(i, df['buy_signal'].iloc[i] * 0.98),  # 文字位置在标记下方
                     color='green',
                     fontweight='bold',
                     fontsize=8,
                     ha='center')  # 文字水平居中对齐
    
    # 卖出信号价格标注
    if not np.isnan(df['sell_signal'].iloc[i]):
        price = df['close'].iloc[i]
        price_text = f'{price:.2f}'
        ax1.annotate(price_text, 
                     xy=(i, df['sell_signal'].iloc[i]),
                     xytext=(i, df['sell_signal'].iloc[i] * 1.01),  # 文字位置在标记上方
                     color='red',
                     fontweight='bold',
                     fontsize=8,
                     ha='center')  # 文字水平居中对齐

# 显示图表
plt = mpf.show()

# 打印交易信号信息
print("\n交易信号:")
buy_indices = np.where(~np.isnan(df['buy_signal']))[0]
sell_indices = np.where(~np.isnan(df['sell_signal']))[0]

if len(buy_indices) > 0:
    print("\n买入信号:")
    for idx in buy_indices:
        print(f"日期: {df.index[idx]}, 价格: {df['close'].iloc[idx]:.2f}")

if len(sell_indices) > 0:
    print("\n卖出信号:")
    for idx in sell_indices:
        print(f"日期: {df.index[idx]}, 价格: {df['close'].iloc[idx]:.2f}")

# print(len(jsonData))

# ticker = 'AAPL'
# start = '2021-12-08'
# interval = '5m'

# data = yf.download(tickers=ticker, start=start,  period='1d', interval=interval)

# print(type(data)); # pandas.core.frame.DataFrame
# print(data)
# mpf.plot(data, type='candle', mav=(5, 10, 20), volume=True)