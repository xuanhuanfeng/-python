# 策略说明：基本思想来源于二八轮动；
# 但做了一个改动：一旦买入一个ETF，直到它动量小于零才卖出
# 于原始策略相比：交易次数减少，回撤也减少，收益更高
# 收盘前7分钟决定是否调仓
# 在雪球网上，我有一些关于ETF定投的资料，雪球ID：江州金猪
# 另有一个ETF定投与量化交易 的QQ群：133815027
# 江州金猪 2016-4-23
import talib
import numpy as np  

def initialize(context):
    # 对比标的
    set_benchmark('000300.XSHG') 
    #设定滑点
    #set_slippage(FixedSlippage(0))
    set_option('use_real_price', True)
    #设置股票池
    stocks = ['159915.XSHE','518880.XSHG']
    g.lastPrice = [0,0]
    g.sarPrice = 0
    g.highPrice = 0 
    # 设置佣金
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0003, min_cost=5))

def getStockPrice(stock, h):
    return h['close'].values[0]

def handle_data(context, data):

        lag = 20 # 回看前20天
        zs2 =  '000300.XSHG' #300指数
        zs8 =  '000905.XSHG'#500指数
        etf300 = '000300.XSHG'#'510300.XSHG'
        etf500 = '510500.XSHG'#'510500.XSHG'
        
        # 获得当前总资产
        value = context.portfolio.portfolio_value
        
        h = attribute_history(etf300, lag, unit='1d', fields=('close','low','high'), skip_paused=True)
        ATR = talib.ATR(np.array(h['high']),np.array(h['low']),np.array(h['close']))
        
        #hs300 = getStockPrice(zs2, lag)
        hs300 = h['close'].values[0]
        #zz500 = getStockPrice(zs8, lag)
        zz500 = h['close'].values[0]
        cp300 = data[zs2].close
        cp500 = data[zs8].close
        ret300 = (cp300 - hs300) / hs300;
        ret500 = (cp500 - zz500) / zz500;
        hold300 = context.portfolio.positions[etf300].total_amount
        hold500 = context.portfolio.positions[etf500].total_amount
        per300 = (g.lastPrice[0]-cp300) *100.0/cp300
        per500 = (g.lastPrice[1]-cp500) *100.0/cp500
        log.info("now = %f,lagPrice = %f,ret = %f",cp300,hs300,ret300)
        
        if cp300 > g.highPrice:
            g.highPrice = cp300
            g.sarPrice = cp300 - 0.8 * ATR[-1]
        
        #record(sarPrice=g.sarPrice)    
        #record(cp300=cp300)
        record(ret300=ret300*10)
        
        #if (ret300 <= 0) and hold300>0:
        
        if ret300>0 and hold300==0:
            g.highPrice = cp300
            g.sarPrice = cp300 - 0.8 * ATR[-1]
            order_target(etf300, value)
            g.lastPrice[0] = cp300
            log.info("买入300")
            
        #if cp300 <= g.sarPrice:
        if (ret300 <= 0) and hold300>0:
            order_target(etf300, 0)
            log.info("卖出300,收益率=%f",per300)
