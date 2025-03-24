import pandas as pd
import yfinance as yf
import mplfinance as mpf
import json
import os
from typing import TypedDict, Dict, Any

# 定义JSON数据的类型结构··
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
# df.index = df.index.rename('date')
# print(df)
R = round(sum(RVals) / len(RVals))
mpf.plot(
  df,
  title='BitMex UBT 15m 2012-12-10 R:' + str(R),
  type='candle',
  style='charles',
  mav=(5, 10, 20),
  volume=True
)
# print(len(jsonData))

# ticker = 'AAPL'
# start = '2021-12-08'
# interval = '5m'

# data = yf.download(tickers=ticker, start=start,  period='1d', interval=interval)

# print(type(data)); # pandas.core.frame.DataFrame
# print(data)
# mpf.plot(data, type='candle', mav=(5, 10, 20), volume=True)