import pandas as pd
import yfinance as yf
import mplfinance as mpf
import json
import os

script_dir = os.path.dirname(__file__)
file_path = os.path.join(script_dir, '20211210.json')

with open(file_path) as fp:
  data = json.load(fp)
  df = pd.DataFrame(data, columns=['timestamp', 'low', 'high', 'open', 'close', 'volume'])
  df['date'] = pd.to_datetime(df['timestamp'])
  df = df.set_index('date')
  # df.index = df.index.rename('date')
  # print(df)
  mpf.plot(df, type='candle', mav=(5, 10, 20), volume=True)
  # print(len(jsonData))

# ticker = 'AAPL'
# start = '2021-12-08'
# interval = '5m'

# data = yf.download(tickers=ticker, start=start,  period='1d', interval=interval)

# print(type(data)); # pandas.core.frame.DataFrame
# print(data)
# mpf.plot(data, type='candle', mav=(5, 10, 20), volume=True)