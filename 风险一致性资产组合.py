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
    #记录上一次调仓的价格和权重
    g.balancePrice = coll.defaultdict(float)
    g.balanceRatio = coll.defaultdict(float)
    

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
    g.stockList = ['510300.XSHG',
                    '518880.XSHG',
                    '511010.XSHG',
                    '513100.XSHG']
    #设置调仓的周期
    g.circleDay = 20
    #设置调仓的价格变化的阀值
    g.priceChangePercent = 0.15
    #设置调仓的权重变化的阀值
    g.ratioChangePercent = 0.25

def needbalance(h,context):
    isBalance = False
    stockValue = context.portfolio.portfolio_value
    if g.balanceDayNum <= 0:
        log.info("已经到下一次定期调仓日")
        isBalance = True
        return isBalance

    for stock in g.stockList:
        #价格变动超过指定限额
        nowPrice = h[stock][-1]

        # try:
        inreasePercent = (nowPrice - g.balancePrice[stock]) / g.balancePrice[stock]
        if inreasePercent > g.priceChangePercent:
            log.info("价格变动超过百分之%f",g.priceChangePercent)
            isBalance = True
            return isBalance

        #权重比重变化超过指定的阀值
        amout = context.portfolio.positions[stock].total_amount
        nowRatio = amout * nowPrice / stockValue
        inreasePercent = (nowRatio - g.balanceRatio[stock]) / g.balanceRatio[stock]
        if inreasePercent > g.ratioChangePercent:
            log.info("权重变动超过百分之%f",g.ratioChangePercent)
            isBalance = True
            return isBalance
        # finally:
        return isBalance
        
'''
主函数
'''
def handle_data(context, data):
    h = history(1, '1d', ('close'),g.stockList,fq=None)

    if needbalance(h,context):
        #调仓
        g.balanceDayNum = g.circleDay
        trade_ratio = stockPosition(0.01,0.017,g.stockList,120,0.95).trade_ratio
        print trade_ratio
        #计算和上次仓位占比的差值，按从小到大排序，优先卖出
        diff_ratio = {}
        for stock in g.stockList:
            diff_ratio[stock] = trade_ratio[stock] - g.balanceRatio[stock]
        sorted(diff_ratio.items(), key=lambda e:e[1], reverse=False)
        print "diff_ratio=",diff_ratio
        
        for stock in g.stockList:
            g.balanceRatio[stock] = trade_ratio[stock]
            g.balancePrice[stock] = h[stock][-1]
        
        #DEBUG
        
        for stock in g.stockList:
            ratio = trade_ratio[stock]
            stock_trade = fun_trade(context,stock,ratio)
        #剩余的钱做现金管理
        price = data['511880.XSHG'].close
        cash = context.portfolio.available_cash
        print 'cash=',cash
        amout = cash / price
        stock_trade = fun_trade(context,'511880.XSHG',ratio)
           
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
    def __init__(self,risk_normal_percent,risk_max_percent,stocklist,lag,confidencelevel):

        #取得股票池中各股票的配比
        self.trade_ratio = self.__fun_get_min_risk(risk_normal_percent,risk_max_percent,confidencelevel,stocklist,lag)
        
        
    def __fun_getdailyreturn(self ,stock ,lag):
        hStocks = attribute_history(stock, lag, '1d', ('close'), skip_paused=True)
        dailyReturns = hStocks.resample('D',how='last').pct_change().fillna(value=0, method=None, axis=0).values
        return dailyReturns
    
    def __fun_calstock_risk_VaR(self,confidencelevel,stocklist,lag):
        __portfolio_VaR = {}
        
        __stock_ratio = {}
        for stock in stocklist:
            dailyReturns = self.__fun_getdailyreturn(stock, lag)
            __portfolio_VaR[stock] = 1 * confidencelevel * np.std(dailyReturns)

            if isnan(__portfolio_VaR[stock]):
                __portfolio_VaR[stock] = 0

        return __portfolio_VaR

    def __fun_get_portfolio_ES(self ,stocklist ,lag ,confidencelevel): 
        a = (1 - confidencelevel)
        ES = 0
        trade_ES = {}
        for stock in stocklist:
            dailyReturns = self.__fun_getdailyreturn(stock,lag)
            dailyReturns_sort =  sorted(dailyReturns)
    
            count = 0
            sum_value = 0
            for i in range(len(dailyReturns_sort)):
                if i < (lag * a):
                    sum_value += dailyReturns_sort[i]
                    count += 1
            if count == 0:
                log.info("stock = %s go into ES = 0,because of count = 0",stock)
                trade_ES[stock] = 0
            else:
                #log.info("stock = %s,sumValue = %f,count = %f",stock,sum_value,count)

                trade_ES[stock] = -(sum_value / (lag * a))

        return trade_ES

    def __fun_get_ratio(self,risk_num,risk_percent,stocklist):
        trade_ratio = {}
        trade_position = {}

        for stock in stocklist:
            trade_position[stock] = round((1.0 / risk_num[stock]),3)
        sum_position = sum(trade_position.values())
        tau = risk_percent * sum_position / len(stocklist)

        #对tau范围进行控制，不能大于1，因为不能加杠杆
        if tau > 1:
            tau = 1

        for stock in stocklist:
            trade_ratio[stock] = round(trade_position[stock] * tau  / sum_position,3)

       
        return trade_ratio

    def __fun_get_min_risk(self,risk_normal_percent,risk_max_percent,confidencelevel,stocklist,lag):
        trade_ratio = {}
        trade_var_ratio = {}
        trade_es_ratio = {}
        portfolio_VaR = {}
        portfolio_ES = {}
        
        portfolio_VaR = self.__fun_calstock_risk_VaR(confidencelevel,stocklist,lag)
        portfolio_ES = self.__fun_get_portfolio_ES(stocklist,lag,confidencelevel)
        trade_var_ratio = self.__fun_get_ratio(portfolio_VaR,risk_normal_percent,stocklist)
        trade_es_ratio = self.__fun_get_ratio(portfolio_ES,risk_max_percent,stocklist)
        for stock in stocklist:
            trade_ratio[stock] = min(trade_var_ratio[stock],trade_es_ratio[stock])
        
        return trade_ratio

        

        
            
            
 
