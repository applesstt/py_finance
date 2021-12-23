import backtrader as bt
import btStrategy as bts
import btDataFrame as btdf
# import matplotlib.pyplot as plt

# plt.style.use('dark_background') # call before plotting

if __name__ == '__main__':
  cerebro = bt.Cerebro()

  btData = bt.feeds.PandasData(dataname = btdf.df)
  # btData = bt.feeds.PandasData(dataname = df, fromdate=datetime.datetime(2021, 12, 11))

  cerebro.adddata(btData)
  # 设置投资金额100000.0
  cerebro.broker.setcash(100000.0)

  cerebro.addsizer(bt.sizers.SizerFix, stake=1)

  #给Cebro引擎添加策略
  cerebro.addstrategy(bts.MoeStrategy)

  #运行Cebro引擎
  cerebro.run()

  # 引擎运行后打期末资金
  # print('组合期末资金: %.2f' % cerebro.broker.getvalue())

  # matplot 版本问题 see:https://stackoverflow.com/questions/63471764/importerror-cannot-import-name-warnings-from-matplotlib-dates
  cerebro.plot(
    loc='grey',
    grid=False
  )
