import numpy as np
import talib

enable_profile()

#定义需要操作的股票池
stocks = ['000300.XSHG']
    
def initialize(context):
    # 设置佣金
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0003, min_cost=5))
    #设定滑点
    set_option('use_real_price', True)
  
    #上一次的交易价格
    g.tradePrice = 0
    #设置动量周期
    g.lag = 20
    #每次交易的额度
    g.perTradeCash = 0
    g.perTradeSellAmt = 0
    #买卖标志
    g.buyFlag = 0  
    g.sellFlag = 0  
    #上一次市场标志，1牛市，0熊市
    g.lastMarket = 1
    #凯利公式
    g.kellyNum = 0

#凯利公式    
def kelly(r,var,tau):
    w_opt = r/var * tau
    if w_opt < 0:
        w_opt = 0
    if w_opt > 1:
        w_opt = 1
    return w_opt

#买卖函数
def tradeStock(stock,msg,money):
    #买卖前处理
    if money <= 0:
        #正在进行卖出操作，其中0代表清空仓位
        pass
    else:
        #正在进行买入操作
        money = g.kellyNum * money
        log.info("money = %f",money)
        
    #买卖交易函数
    if money ==  0:
        order_target_value(stock, 0)
    else:
        order_value(stock, money)
    #输出提示信息
    log.info(msg)
    
    
#按照网格交易法进行交易
def gridTrade(stock,dlStock,atr,nowPrice,upPercent,downPercent,tradePercent,basePercent,sellAmt,cash):
    '''
    '''
    #获取买卖标志

  
    if sellAmt == 0:
        #建立底仓
        tmpTotalCash = cash
        cash = cash * basePercent
        #根据网格计算每次交易的额度
        g.perTradeCash = (tmpTotalCash-cash) * tradePercent
        g.perTradeSellAmt = cash * tradePercent
        #买入股票
        tradeStock(stock,"buid base position,Buying " + stock + ',' + '%s' %cash,cash)
        #更新上一次的交易金额
        g.tradePrice = nowPrice
    else:
        if nowPrice >= g.tradePrice * (1+upPercent) and g.tradePrice > 0 and sellAmt > 0 and sellAmt >= g.perTradeSellAmt:
            #价格上涨，触发网格卖出交易
            #计算卖出的份额
            if sellAmt >= g.perTradeSellAmt:
                sellAmt = g.perTradeSellAmt 
            #卖出股票
            tradeStock(stock,"Selling " + stock + ',' + '%s' %sellAmt,-sellAmt)
            #更新上一次的交易金额
            g.tradePrice = nowPrice

        elif nowPrice <= g.tradePrice  * (1-downPercent) or (nowPrice >= g.tradePrice * (1+upPercent) and sellAmt < g.perTradeSellAmt):
            #价格下跌，触发网格买入交易
            #计算买入的份额
            #非建立底仓的情况下
            if cash >= g.perTradeCash:
                cash = g.perTradeCash
            #根据网格计算每次卖出交易的额度   
            g.perTradeSellAmt = (cash + sellAmt) * tradePercent
            #买入股票
            tradeStock(stock,"Buying " + stock + ',' + '%s' %cash,cash)
            #更新上一次的交易金额
            g.tradePrice = nowPrice

        '''
        elif nowPrice <= g.sarPrice:
            #卖出股票
            order_target_value(stock, 0)
            log.info("Selling All %s",stock)
            g.sellFlag = 0
            #更新上一次的交易金额
            g.tradePrice = nowPrice
        '''
        
    #DEBUG
    #record(cash=cash)
    #record(sellAmt=sellAmt)
   
#按照趋势使用动量进行交易 
def motionTrade(stock,dlStock,h,cash,sellAmt):
    #进行补仓
    if dlStock > 0 and sellAmt == 0:
        #买入股票
        tradeStock(stock,"Buying " + stock + ',' + '%s' %cash,cash)
        #更新上一次的交易金额
        g.tradePrice = h['close'][-1]
        
    #趋势结束，进行卖出操作
    if dlStock <= 0 and sellAmt > 0:
        #卖出股票
        tradeStock(stock,"Selling " + stock + ',' + '%s' %0,0)
        #更新上一次的交易金额
        g.tradePrice = h['close'][-1]
        
# 每个单位时间(如果按天回测,则每天调用一次,如果按分钟,则每分钟调用一次)调用一次
def handle_data(context, data):

    for stock in stocks:
        #计算各种线的指标
        short = 9
        mid = 26
        longT = 52
        
        h = attribute_history(stock, mid+longT, '1d', ('open','close','high','low'), skip_paused=True)
        turnLine = (h['high'][-short:].max()+h['low'][-short:].min()) / 2.0
        baseLine = (h['high'][-mid:].max()+h['low'][-mid:].min()) / 2.0
            
        temA = (h['high'][-(mid+short):-mid].max()+h['low'][-(mid+short):-mid].min()) / 2.0
        temB = (h['high'][-longT:-mid].max()+h['low'][-longT:-mid].min()) / 2.0
        cloudUpLine = (temA + temB) / 2.0
            
        cloudDwonLine = (h['high'][0:-mid].max()+h['low'][0:-mid].min()) / 2.0
            
        lateLine = h['close'][-(mid+1)]

        downCloudLine = min(cloudUpLine,cloudDwonLine)
        
        #计算凯利公式
        p = h['close'][-g.lag:]
        ret = p.pct_change().dropna().values
        r = np.mean(ret)
        var = np.var(ret) 
        g.kellyNum = kelly(r,var,1)
        
        # 取得当前的现金
        cash = context.portfolio.cash
        sellAmt = context.portfolio.positions_value
        

        '''
        买卖决策函数
        '''
        
        ATR = talib.ATR(np.array(h['high']),np.array(h['low']),np.array(h['close']))
    
        lastClosePrice = h['close'][-1]
        #计算动量
        dlStock = (lastClosePrice-h['close'][-g.lag]) / h['close'][-g.lag]

            
        #当市场处于牛熊分界线下方也就是熊市的时候，实行网格交易
        if lastClosePrice <= downCloudLine:

            if (g.lastMarket == 1 and dlStock > 0) or g.lastMarket == 0:
                g.lastMarket = 0
                #DEBUG
                log.info("卖出nowPrice %f,tradePrice %f,tradePrice %f sellAmt %f",h['close'][-1] ,g.tradePrice * (1+0.02),g.tradePrice,sellAmt)
                log.info("买入nowPrice %f,tradePrice %f,tradePrice %f cash %f",h['close'][-1] ,g.tradePrice * (1-0.04),g.tradePrice,cash)
                #gridTrade(stock,dlStock,atr,nowPrice,upPercent,downPercent,tradePercent,basePercent,sellAmt,cash):
                gridTrade(stock,dlStock,ATR[-1],lastClosePrice,0.05,0.03,0.8,0.3,sellAmt,cash)
           
        #当市场处于牛熊分界线上方也就是牛市的时候，实行趋势追踪交易
        else:
            g.lastMarket = 1
            #motionTrade(stock,dlStock,h,cash,sellAmt):
            motionTrade(stock,dlStock,h,cash,sellAmt)
  
                
        #DEBUG 
        #输出各种线指标
        record(atr=dlStock*10)
    
        record(kellyNum=g.kellyNum)
        #record(trend=g.trendList[-1])
        
            
            
 
