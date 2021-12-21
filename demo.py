import pandas as pd
import yfinance as yf
import mplfinance as mpf
import json
import os

script_dir = os.path.dirname(__file__)
file_path = os.path.join(script_dir, '20211210.json')
formatedData = []
RVals = []

with open(file_path) as fp:
  data = json.load(fp)
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