import pandas as pd
import json
import os

script_dir = os.path.dirname(__file__)
fileNames = [
  '20211011',
  '20211014',
  '20211017',
  '20211020',
  '20211023',
  '20211026',
  '20211029',
  '20211101',
  '20211104',
  '20211107',
  '20211110',
  '20211113',
  '20211116',
  '20211119',
  '20211122',
  '20211125',
  '20211128',
  '20211201',
  '20211204',
  '20211207',
  '20211210'
]
# formatedData = []
# RVals = []
allData = []

for fileName in fileNames:
  file_path = os.path.join(script_dir, 'data/' + fileName + '.json')

  with open(file_path) as fp:
    data = json.load(fp)
    allData = allData + data
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

df = pd.DataFrame(allData, columns=['timestamp', 'low', 'high', 'open', 'close', 'volume'])
df['date'] = pd.to_datetime(df['timestamp'])
df = df.set_index('date')