import pandas as pd
import json
import os

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