import numpy as np
import talib
import pandas
import scipy as sp
import scipy.optimize
import datetime as dt
from scipy import linalg as sla
from scipy import spatial
import collections as   coll

enable_profile()


#initialize只会运行一遍    
def initialize(context):
    set_benchmark('000300.XSHG')
    #设置买卖手续费，万三，最小 5 元
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0003, min_cost=5))
    set_slippage(FixedSlippage(0.002))
    set_option('use_real_price', True)

    # 关闭部分log
    #log.set_level('order', 'error')

    #设定网格最低仓位阀值
    g.minPercent = 0.1
    #上一次的交易价格
    g.tradePrice = coll.defaultdict(int)
    #上一次市场标志，1牛市，0熊市
    g.bearMarket = coll.defaultdict(int)
    #记录上一次满仓的仓位
    g.lastAmout = coll.defaultdict(int)
    #记录上一次指标的值
    g.lastTurnLine = coll.defaultdict(int)
    g.lastBaseLine = coll.defaultdict(int)
    g.lastBearLine = coll.defaultdict(int)
    g.lastBullLine = coll.defaultdict(int)
    g.lastMidLine  = coll.defaultdict(int)

    #设置建仓交易是否成功
    g.isOneLevelBuyFail   = coll.defaultdict(int)
    g.isTwoLevelBuyFail   = coll.defaultdict(int)
    g.isThirdLevelBuyFail = coll.defaultdict(int)
    
    #记录下一次调仓的日期距离当天的天数
    g.balanceDayNum = 0
    

'''
模拟盘在每天的交易时间结束后会休眠，第二天开盘时会恢复，如果在恢复时发现代码已经发生了修改，则会在恢复时执行这个函数。 
具体的使用场景：可以利用这个函数修改一些模拟盘的数据。之前发现部分代码在before_trading_start进行重新赋值，和这有异曲同工之妙
注意: 因为一些原因, 执行回测时这个函数也会被执行一次, 在 initialize 执行完之后执行.
'''
def after_code_changed(context):
    pass

'''
该函数会在每天开始交易前被调用一次, 您可以在这里添加一些每天都要初始化的东西.
'''
def before_trading_start(context):
    #初始化
    fun_initialize(context)

'''
该函数被before_trading_start调用，用以作为每天的初始化，以防止被模拟盘恢复数据时候覆盖
同时全局变量用g，不用context，因为context本身含有系统定义的变量，有可能会出现重名导致用户定义的变量覆盖系统变量
'''
def fun_initialize(context):
    #设置买入的网格
    g.buyGird = {0.4:0,0.7:0,0.9:0,1:0}
    #设置卖出的网格
    g.sellGird = {0.4:0,0.1:0,0:0}
    #设置处理的股票池
    g.stockList = ['510300.XSHG','510500.XSHG','159915.XSHE','510050.XSHG',
                    '160216.XSHE','518880.XSHG','162411.XSHE',
                    '511010.XSHG','511220.XSHG',
                    '513100.XSHG']
    #设置调仓的周期
    g.circleDay = 30
    

'''
主函数
'''
def handle_data(context, data):
    if g.balanceDayNum <= 0:
        #调仓
        g.balanceDayNum = g.circleDay
        trade_ratio = stockPosition(g.stockList,180,0.95).trade_ratio
        total_ratio = sum(trade_ratio.values())
        for stock in g.stockList:
            ratio = trade_ratio[stock]
            stock_trade = fun_trade(context,stock,ratio)
            log.info("stock = %s,ratio = %f,trade_ratio = %f",stock,ratio,total_ratio)
    else:
        g.balanceDayNum -= 1
        

'''
交易类，主要产生买入，卖出信号，以及仓位控制
'''
class fun_trade():
    #初始函数
    def __init__(self,context,stock,ratio): 
        
        self.cash = context.portfolio.available_cash * ratio
        self.total_amout = context.portfolio.positions[stock].total_amount
        self.value = context.portfolio.portfolio_value * ratio
        self.tau = 1
        self.stock = stock
        self.h = attribute_history(stock, 100, '1d', ('close'), skip_paused=True)
        self.price = (self.h)['close'][-1]
        self.lastprice = (self.h)['close'][-2]  
        self.stockRet = self.price / (self.h)['close'][-20]
        self.lastStockRet = self.lastprice / (self.h)['close'][-21]

        self.computeHA()
        self.bearLine = min(self.cloudUpLine,self.cloudDwonLine)
        self.bullLine = max(self.cloudUpLine,self.cloudDwonLine)
        self.midLine = (self.cloudUpLine+self.cloudDwonLine)/2

        #调用交易函数
        self.trade()

        g.lastTurnLine[stock] = self.turnLine
        g.lastBaseLine[stock] = self.baseLine
        g.lastBearLine[stock] = self.bearLine
        g.lastBullLine[stock] = self.bullLine
        g.lastMidLine[stock]  = self.midLine 

        

         
        
    #交易函数
    def trade(self):
        price = self.price
        #按照新的份额进行调整
        self.adjustPosition()
        '''
        if price >= self.bearLine: 
            #采取趋势策略
            self.motionTrade()

        elif price < self.bearLine and g.bearMarket[self.stock] == 0 \
            and self.total_amout > 0:
            #对趋势交易进行清仓
            log.info("Motion Selling All,amout is %f",self.total_amout)
            self.tradeStock(0)

        elif (g.bearMarket[self.stock] == 0 and self.turnLine >= self.baseLine) \
            or g.bearMarket[self.stock] == 1:  
            #采取网格交易策略
            self.gridTrade(0.03,0.05)
        '''  

    #调整份额
    def adjustPosition(self):
        #计算现有的比例基金应该持有的份额
        nowAmout = self.value / self.price 
        lastAmout = self.total_amout
        diffAmout = nowAmout-lastAmout
        #log.info("nowAmout = %f,lastAmout = %f diffAmout = %f",nowAmout,lastAmout,diffAmout)
        #若份额大于1手，则开始交易
        if (abs(diffAmout) >= 100):
            self.tradeStock(diffAmout)



 
            

    #计算指标
    def computeHA(self,short = 8,mid = 21,longT = 55):
        
        #计算各种线的指标
        h = attribute_history(self.stock, mid+longT, '1d', ('open','close','high','low'), skip_paused=True)
        self.turnLine = (h['high'][-short:].max()+h['low'][-short:].min()) / 2.0
        self.baseLine = (h['high'][-mid:].max()+h['low'][-mid:].min()) / 2.0
            
        temA = (h['high'][-(mid+short):-mid].max()+h['low'][-(mid+short):-mid].min()) / 2.0
        temB = (h['high'][-longT:-mid].max()+h['low'][-longT:-mid].min()) / 2.0
        self.cloudUpLine = (temA + temB) / 2.0
            
        self.cloudDwonLine = (h['high'][0:-mid].max()+h['low'][0:-mid].min()) / 2.0
            
        lateLine = h['close'][-(mid+1)]
        


    #凯利公式
    def kelly(self): 
        h = self.h
        ret = h['close'].pct_change().dropna().values
        r = np.mean(ret)
        var = np.var(ret) 
        w_opt = r/var * self.tau
        if w_opt < 0:
            w_opt = 0
        if w_opt > 1:
            w_opt = 1
        return w_opt

    #买卖函数
    def tradeStock(self,amout):

        total_value = self.value
        cash = self.cash
        price = self.price
        total_amout = self.total_amout
        stock = self.stock
        
        #买卖前处理
        amout = round(amout / 100) * 100
        if amout < 0:
            #正在进行卖出操作
            if abs(amout) > total_amout and amout < 100:
                amout += 100
            if total_amout == 0:
                ratio = 0
            else:
                ratio = abs(amout) / total_amout
            msg = ("Selling " + stock + ", amout=" + str(amout) + ", money=" + str(price*amout) + ", ratio=" + str(ratio))
        elif amout == 0:
            #0代表清空仓位
            msg = ("Selling All" + stock + ",amout=" + str(total_amout) + ", money=" + str(price*amout)) 
        else:
            #正在进行买入操作
            if price*amout > cash and amout > 100:
                amout -= 100
            if total_value == 0:
                ratio = 0  
            else:
                ratio = price*amout / total_value
            msg = "Buying " + stock + ",amout=" + str(amout) + ", money=" + str(price*amout) + ", ratio=" + str(ratio)
            
        #买卖交易函数
        if amout ==  0:
            rc = order_target_value(stock, 0)
            g.lastAmout[stock] = 0
        else:
            rc = order(stock,amout)
        #输出提示信息
        if rc is None:
                log.info("order failed,stock=%s,amout=%f",stock,amout)
        log.info(msg)
        g.tradePrice[stock] = price
        if amout > g.lastAmout[stock]:
            g.lastAmout[stock] = amout
    
    #按照网格交易法进行交易
    def gridTrade(self,upPercent,downPercent):
        '''
        '''
        stock = self.stock
        price = self.price

        #买入操作
        if price <= g.tradePrice[stock]  * (1-downPercent) and self.cash > 0:
            
            #获取凯利系数
            ratio = self.kelly()
            log.info("into buy %f,ratio is %f",self.cash,ratio)
            for i in g.buyGird.keys():
                if g.buyGird[i] == 0:
                    p = i
                    break
            else:
                #如果已经遍历一遍，初始化买入各档次设定
                n = 0
                for i in g.buyGird.keys():
                    if n == 0:
                        p = i
                    else:
                        g.buyGird[i] = 0
            #买入
            canBuyAmout = self.cash / price
            tmpAmout = canBuyAmout * p
            log.info("into canBuyAmout %f,tmpAmout is %f",canBuyAmout,tmpAmout)
            if tmpAmout >= 100:
                log.info("Gird buying,kelly ratio is %f, level is %f,amout is %f",ratio,p,tmpAmout)
                self.tradeStock(tmpAmout)
                g.bearMarket[self.stock] = 1
            g.buyGird[p] = 1 

        #价格上涨，触发网格卖出交易
        if price >= g.tradePrice[stock] * (1+upPercent) and self.total_amout > 0:
            for i in g.sellGird.keys():
                if g.sellGird[i] == 0:
                    p = i
                    break
            else:
                #如果已经遍历一遍，初始化卖出各档次设定
                n = 0
                for i in g.sellGird.keys():
                    if n == 0:
                        p = i
                    else:
                        g.sellGird[i] = 0
            #计算卖出的金额
            sellAmt = p * g.lastAmout[stock] - self.total_amout 
            #卖出股票
            if sellAmt <= -100:
                log.info("Gird selling, level is %f,amout is %f",p,sellAmt)
                self.tradeStock(sellAmt)
            g.sellGird[p] = 1


   
    #按照趋势使用动量进行交易 
    def motionTrade(self):
        
        holdAmout = self.total_amout
        price = self.price
        tmpAmout = 0
        canBuyAmout = self.cash / price
        isBuy = False
        isSell = False
        stock = self.stock

        if holdAmout > 0:
            #减仓
            if price <= self.midLine and self.lastprice > g.lastMidLine[stock]:
                #卖出股票到只剩0.5成股票
                tmpAmout = 0.05 * g.lastAmout[stock] - holdAmout
                #log.info("5,totalAmout %f,holdAmout %f,tmpAmout %f",g.lastAmout[stock],holdAmout,tmpAmout)
                p = 5
                isSell = True
            elif price <= self.bullLine and self.lastprice > g.lastBullLine[stock]:
                #卖出股票到只剩2成股票
                tmpAmout = 0.2 * g.lastAmout[stock] - holdAmout
                #log.info("30,totalAmout %f,holdAmout %f,tmpAmout %f",g.lastAmout[stock],holdAmout,tmpAmout)
                p = 20
                isSell = True
            elif(g.lastTurnLine[stock] >= g.lastBaseLine[stock] and self.turnLine < self.baseLine) \
                 or (self.lastprice >= g.lastBearLine[stock] and price < self.baseLine) \
                 or (self.lastStockRet >= 0 and self.stockRet < 0):
                #卖出股票到只剩4成股票
                tmpAmout = 0.4 * g.lastAmout[stock] - holdAmout
                #log.info("60,totalAmout %f,holdAmout %f,tmpAmout %f",g.lastAmout[stock],holdAmout,tmpAmout)
                p = 40
                isSell = True

            if isSell:
                if tmpAmout <= 0:
                    if tmpAmout >= -100:
                        log.info("Motion stock Amout lest than 100 to sell, level is %f,amout is %f",p,tmpAmout)
                    else:
                        log.info("Motion selling to level is %f,amout is %f",p,tmpAmout)
                        self.tradeStock(tmpAmout) 
                else:
                    log.info("Motion stock Amout larger than 0 to sell")
                    isSell = False
        
        #进行补仓
        if ((g.bearMarket[stock] == 0 and price >= self.bullLine) \
            or g.bearMarket[stock] == 1) and canBuyAmout >= 100 \
            and not isSell:

            totalAmout = (holdAmout + canBuyAmout)
            amout = 0
            ratio = self.kelly()

            #log.info("into Motion,holdAmout %f,totalAmout %f",holdAmout,totalAmout)
            if (self.lastprice < g.lastBullLine[stock] and price >= self.bullLine) \
                or g.isThirdLevelBuyFail[stock] == 1:
                #建5成仓
                if ratio > 0:
                    amout += (0.5 * totalAmout)
                    p = 50
                    isBuy = True
                    g.isThirdLevelBuyFail[stock] = 0
                else:
                    g.isThirdLevelBuyFail[stock] = 1

            if (self.lastprice < g.lastBearLine[stock]  and price >= self.bearLine) \
                or g.isTwoLevelBuyFail[stock] == 1:
                #建3成仓
                if ratio > 0:
                    amout += (0.3 * totalAmout)
                    p = 30
                    isBuy = True
                    g.isTwoLevelBuyFail[stock] = 0
                else:
                    g.isTwoLevelBuyFail[stock] = 1

            if (g.lastTurnLine[stock] < g.lastBaseLine[stock] and self.turnLine >= self.baseLine) \
                 or (self.lastprice < g.lastBearLine[stock] and price >= self.baseLine) \
                 or (self.lastStockRet < 0 and self.stockRet >= 0) \
                 or g.isOneLevelBuyFail[stock] == 1:
                #建2成仓
                if ratio > 0:
                    amout += (0.2 * totalAmout)
                    p = 20
                    isBuy = True
                    g.isOneLevelBuyFail[stock] = 0
                else:
                    g.isOneLevelBuyFail[stock] = 1

            record(isOneLevelBuyFail = g.isOneLevelBuyFail[stock])
            record(isTwoLevelBuyFail = g.isTwoLevelBuyFail[stock])
            record(isThirdLevelBuyFail = g.isThirdLevelBuyFail[stock])
            if ratio == 0:
                log.info("Motion stock do not buy because ratio is 0")
            elif isBuy:
                g.bearMarket[self.stock] = 0    
                if amout >= 0:
                    if amout >= 100:
                        log.info("Motion buying to full,kelly ratio is %f, level is %f,amout is %f",ratio,p,amout)
                        self.tradeStock(amout) 
                    else:
                        log.info("Motion stock Amout lest than 100 to buy,kelly ratio is %f, level is %f,amout is %f",ratio,p,amout)
                else:
                    log.info("Motion stock Amout less than 0 to buy")
        
            

'''
确定资产组合的配比
'''    
class stockPosition():
    def __init__(self, stocklist,lag ,confidencelevel):
        trade_ES = {}
        self.trade_ratio = {}
        
        for stock in stocklist:
            trade_ES[stock] = self.__fun_get_portfolio_ES(stock ,lag ,confidencelevel)
        #取得股票池中各股票的配比
        trade_ratio = self.trade_ratio = self.__fun_caltraderatio(trade_ES, stocklist)
        
        
    def __fun_getdailyreturn(self,stock ,lag):
        hStocks = history(lag, '1d', 'close', stock, df=True)
        dailyReturns = hStocks.resample('D',how='last').pct_change().fillna(value=0, method=None, axis=0).values 
        return dailyReturns

    def __fun_get_portfolio_ES(self ,stock ,lag ,confidencelevel): 
        a = (1 - confidencelevel)
        ES = 0
        if stock:
            dailyReturns = self.__fun_getdailyreturn(stock,lag)
            dailyReturns_sort =  sorted(dailyReturns)
    
            count = 0
            sum_value = 0
            for i in range(len(dailyReturns_sort)):
                if i < (lag * a):
                    sum_value += dailyReturns_sort[i]
                    count += 1
            if count == 0:
                ES = 0
            else:
                ES = -(sum_value / (lag * a))

        return ES
        
    def __fun_caltraderatio(self ,trade_ES, stocklist):
         trade_ratio = {}
         trade_position = {}
         max_position = max(trade_ES.values()) 
         for stock in stocklist:
             trade_position[stock] = round((max_position / trade_ES[stock]),3)

         total_position = sum(trade_position.values())

         for stock in stocklist:
             trade_ratio[stock] = round((trade_position[stock] / total_position),3)
         return trade_ratio
        

        
            
            
 
