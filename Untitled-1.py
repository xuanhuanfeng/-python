import numpy as np
import talib
import pandas
import scipy as sp
import scipy.optimize
import datetime as dt
from scipy import linalg as sla
from scipy import spatial

enable_profile()

#定义需要操作的股票池
stocks = ['000300.XSHG']

#initialize只会运行一遍    
def initialize(context):
    set_benchmark('511010.XSHG')
    #设置买卖手续费，万三，最小 5 元
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0003, min_cost=5))
    set_slippage(FixedSlippage(0.002))
    set_option('use_real_price', True)

    # 关闭部分log
    #log.set_level('order', 'error')

    #设定网格最低仓位阀值
    g.minPercent = 0.1
    #上一次的交易价格
    g.tradePrice = 0
    #上一次市场标志，1牛市，0熊市
    g.lastMarket = 1
    #记录上一次交易的价格
    g.lastPrice = {}
    #记录上一次满仓的仓位
    g.lastAmout = {}

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
    #主函数，生成策略
    main(context)
'''
该函数被before_trading_start调用，用以作为每天的初始化，以防止被模拟盘恢复数据时候覆盖
同时全局变量用g，不用context，因为context本身含有系统定义的变量，有可能会出现重名导致用户定义的变量覆盖系统变量
'''
def fun_initialize(context):
    pass

'''
主函数
'''
def main(context):
    pass

'''
交易类，主要产生买入，卖出信号，以及仓位控制
'''
class fun_trade():
    #初始函数
    def __init__(self,context,stock,ratio,lag,price): 
        self.price = price
        self.cash = context.portfolio.available_cash * ratio
        self.total_amout = context.portfolio.positions[stock].total_amount
        self.lag = lag
        self.tau = 1

        #调用交易函数
        self.trade()

    #交易函数
    def trade(self)：
        self.computeHA()
        self.bearLine = min(self.cloudUpLine,self.cloudDwonLine)
        self.bullLine = max(self.cloudUpLine,self.cloudDwonLine)
        self.midLine = (self.cloudUpLine+self.cloudDwonLine)/2

        #采取趋势策略
        if (g.lastMarket = 1 and  price >= bullLine) \ 
            or (g.lastMarket = 0 and  price >= bearLine):
            self.motionTrade

    
    #按照趋势使用动量进行交易 
    def motionTrade(self,stock,dlStock,h,cash,sellAmt):
        price = self.price
        #进行补仓
        if price > self.baseLine or self.turnline
    #凯利公式    
    def kelly(self):
        
        h = attribute_history(stock, self.lag, '1d', ('close'), skip_paused=True)
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
def tradeStock(self,amout,price):
        
        g.lastPrice[self.stock] = price
        total_value = self.total_value
        cash = self.cash
        total_amout = self.total_amout
        
        #买卖前处理
        amout = round(amout)
        if amout < 0:
            #正在进行卖出操作
            if abs(amout) > total_amout:
                amout += 100
            ratio = abs(amout) / total_amout
            msg = ("Selling " + stock + ", amout=" + str(amout) + ", money=" + str(price*amout) + ", ratio=" + str(ratio))
        elif amout == 0:
            #0代表清空仓位
            msg = ("Selling All" + stock + ",amout=" + str(total_amout) + ", money=" + str(price*amout)) 
        else:
            #正在进行买入操作
            if price*amout > cash:
                amout -= 100
            ratio = price*amout / total_value
            msg = ("Buying " + stock + ",amout=" + str(amout) + ", money=" + str(price*amout))
            
        #买卖交易函数
        if amout ==  0:
            rc = order_target_value(stock, 0)
        else:
            rc = order(stock,amout)
        #输出提示信息
        if rc is None:
                log.info("order failed,stock=%s,amout=%f",stock,amout)
        log.info(msg)
    
    #按照网格交易法进行交易
    def gridTrade(self,stock,upPercent,downPercent,percent,basePercent):
        '''
        '''
        #建立底仓
        if self.total_amout / (self.total_amout + self.cash) == g.minPercent:
            #获取凯利系数
            ratio = self.kelly()
            cash = self.cash * basePercent * ratio
            #买入股票
            self.tradeStock(stock,cash)

        else:
            #价格上涨，触发网格卖出交易
            if self.newprice >= g.tradePrice * (1+upPercent) and self.total_amout > 0:
                #计算卖出的金额
                sellAmt = self.total_amout * self.newprice * percent
                #卖出股票
                tradeStock(stock,-sellAmt)

            #价格下跌，触发网格买入交易
            elif nowPrice <= g.tradePrice  * (1-downPercent) or (nowPrice >= g.tradePrice * (1+upPercent) and sellAmt < g.perTradeSellAmt):
                
                #获取凯利系数
                ratio = self.kelly()
                cash = self.cash * percent * ratio
                #买入股票
                tradeStock(stock,cash)

   
    #按照趋势使用动量进行交易 
    def motionTrade(stock,dlStock,h,cash,sellAmt):
        #进行补仓
        if dlStock > 0:
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
            
    #计算指标
    def computeHA(self,short = 8,mid = 21,longT = 55):
        
        
        #计算各种线的指标
        h = attribute_history(s tock, mid+longT, '1d', ('open','close','high','low'), skip_paused=True)
        self.turnLine = (h['high'][-short:].max()+h['low'][-short:].min()) / 2.0
        self.baseLine = (h['high'][-mid:].max()+h['low'][-mid:].min()) / 2.0
            
        temA = (h['high'][-(mid+short):-mid].max()+h['low'][-(mid+short):-mid].min()) / 2.0
        temB = (h['high'][-longT:-mid].max()+h['low'][-longT:-mid].min()) / 2.0
        self.cloudUpLine = (temA + temB) / 2.0
            
        self.cloudDwonLine = (h['high'][0:-mid].max()+h['low'][0:-mid].min()) / 2.0
            
        lateLine = h['close'][-(mid+1)]
        
    

    
class stockPosition():