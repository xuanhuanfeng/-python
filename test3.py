# 策略说明：基本思想来源于二八轮动；
# 但做了一个改动：一旦买入一个ETF，直到它动量小于零才卖出
# 于原始策略相比：交易次数减少，回撤也减少，收益更高
# 收盘前7分钟决定是否调仓
# 在雪球网上，我有一些关于ETF定投的资料，雪球ID：江州金猪
# 另有一个ETF定投与量化交易 的QQ群：133815027
# 江州金猪 2016-4-23
import talib
import numpy as np  
import time

stock = '000839.XSHE'

def initialize(context):
    # 对比标的
    set_benchmark(stock) 
    #设定滑点
    #set_slippage(FixedSlippage(0))
    set_option('use_real_price', True)
    #设置股票池
    stocks = ['159915.XSHE','518880.XSHG']
    g.lastPrice = {}
    g.sarPrice = 0
    g.highPrice = 0 
    # 设置佣金
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0003, min_cost=5))

def getStockPrice(stock, h):
    return h['close'].values[0]

def zuliValue(y,v):
    highSum = 0
    totalSum = 0
    lag = len(y)
    base = np.log(lag+1)
    
    for i in range(lag):
        if y[i] != y[-1]:
            tmp = v[i] * np.log(1.0/np.abs(y[i]-y[-1])*y[-1]) * (np.log(i+1)/base)
            totalSum += tmp
        
        if y[i] > y[-1]:
            highSum +=  tmp

    if totalSum != 0:
        result = highSum/totalSum
    else:
        result = 0
    

    return result

class HA():
    def __init__(self,context,stock):
        self.newprice = context.portfolio.positions[stock].price
        self.cash = context.portfolio.available_cash
        self.total_amout = context.portfolio.positions[stock].total_amount

        self.tau = 1
        self.stock = stock
        self.computeHA()
        
    #计算指标
    def computeHA(self,short = 8,mid = 21,longT = 55):
        
        
        #计算各种线的指标
        h = attribute_history(stock, mid+longT, '1d', ('open','close','high','low'), skip_paused=True)
        self.turnLine = (h['high'][-short:].max()+h['low'][-short:].min()) / 2.0
        self.baseLine = (h['high'][-mid:].max()+h['low'][-mid:].min()) / 2.0
            
        temA = (h['high'][-(mid+short):-mid].max()+h['low'][-(mid+short):-mid].min()) / 2.0
        temB = (h['high'][-longT:-mid].max()+h['low'][-longT:-mid].min()) / 2.0
        self.cloudUpLine = (temA + temB) / 2.0
            
        self.cloudDwonLine = (h['high'][0:-mid].max()+h['low'][0:-mid].min()) / 2.0
            
        lateLine = h['close'][-(mid+1)]   

        #买卖函数
    def tradeStock(self,amout,price):
        
        g.lastPrice[self.stock] = newprice
        cash = self.cash
        total_amout = self.total_amout
        ratio = abs(amout) / total_amout
        amout = 0
        
        #买卖前处理
        amout = round(amout)
        if amout < 0:
            #正在进行卖出操作
            if abs(amout) > total_amout:
                amout += 100
            msg = ("Selling " + stock + ", amout=" + str(amout) + ", money=" + str(price*amout) + ", ratio=" + str(ratio))
        elif amout == 0:
            #0代表清空仓位
            msg = ("Selling All" + stock + ",amout=" + str(total_amout) + ", money=" + str(price*amout)) 
        else:
            #正在进行买入操作
            if price*amout > cash:
                amout -= 100
            msg = ("Buying " + stock + ",amout=" + str(amout) + ", money=" + str(price*amout))
            
        #买卖交易函数
        if money ==  0:
            rc = order_target_value(stock, 0)
        else:
            rc = order(stock,amout)
        #输出提示信息
        if rc is None:
                log.info("order failed,stock=%s,amout=%f",stock,amout)
        log.info(msg)
        
def handle_data(context, data):

        lag = 180 # 回看前20天
        
        hold300 = context.portfolio.positions[stock].total_amount
        # 获得当前总资产
        value = context.portfolio.portfolio_value
        
        
        
        h = attribute_history(stock, lag+1, '1d', ('open','close','high','low','volume'), skip_paused=True)
        maxP = max(h['close'].values[:lag])
        cp300 = h['close'][-1]
        ret = (cp300-h['close'][1])*100/h['close'][1]
        zx = 1
        zx = zuliValue(h['close'],h['volume'])

        #record(zx=zx)
        #record(up=0.6)
        #record(down=0.4)
        
        ha = HA(context,stock)
        up = max(ha.cloudUpLine,ha.cloudDwonLine)
        down = min(ha.cloudUpLine,ha.cloudDwonLine)
        mid = (ha.cloudUpLine+ha.cloudDwonLine)/2
        
        if cp300 >= up:
            if hold300 == 0:
                ha.tradeStock(value,cp300)
            elif ha.turnLine <= ha.baseLine and hold300 > 0:
                ha.tradeStock(-value*0.5,cp300)
        elif cp300 >= mid and cp300 < up and hold300 > 0:
            ha.tradeStock(-value*0.3,cp300)
        elif cp300 >= down and cp300 < mid and hold300 > 0:
            ha.tradeStock(-value*0.1,cp300)
        elif hold300 > 0:
            ha.tradeStock(0,cp300)
        
        #if (ret300 <= 0) and hold300>0:
        
        #if ret >  0  and hold300==0:
        #if cp300 >  maxP  and hold300==0:
        '''
        if zx <= 0.5 and hold300==0:  
            order_target(stock, value)
            log.info("买入300")
            
        #if ret < 0 and hold300 > 0:
        #if (ret300 <= 0) and hold300>0:
        if zx > 0.6 and hold300 > 0:
            order_target(stock, 0)
            log.info("卖出300")
        '''
