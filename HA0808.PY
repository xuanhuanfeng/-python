enable_profile()

#定义需要操作的股票池
stocks = ['000300.XSHG']

def computeNewK(stock,count):
    h = attribute_history(stock, count, '1d', ('open','close','high','low'), None)
    open_price = h['open'][0]
    close_price = h['close'][0]
    
    for i in range(1,len(h['open'])-1):
        newClosePrice = (h['open'][i] + h['close'][i] + h['high'][i] + h['low'][i]) / 4.0
        newOpenPrice  = (open_price + close_price) / 2.0
        open_price = newOpenPrice
        close_price = newClosePrice

    return newOpenPrice,newClosePrice
    
def initialize(context):
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0003, min_cost=5))
    
    # 初始化前天的HA开盘价和收盘价
    g.lastNewOpenPrice = 0  
    g.lastNewClosePrice = 0
    #趋势
    g.upOrDown = 2
    #逆转
    g.isTurn = False
    #趋势延续天数
    g.dayNum = [0,0,0]
    #回调趋势延续天数
    g.turnDayNum = 1
    #回调趋势最长延续天数
    g.mostTurnDayNum = 0
    #记录买入的仓位
    g.buyPosition = 0
    #记录卖出的仓位
    g.sellPosition = 0
    #第一段的开始价格
    g.startPrice = -1
    #第一段的开始价格
    g.startPrice = -1
    #第二段的开始价格
    g.tmpPrice = -1
    #第三段的开始价格
    g.endPrice = -1
    
    #新增趋势队列
    g.trendList = []
    #价格状态
    g.stat = 0
    

#计算HA数值
def computeHaValue(stock,short = 9,mid = 26,longT = 52):
    '''
    全局变量：
    昨日HA的开盘数值：g.lastNewOpenPrice
    昨日HA的收盘数值：g.lastNewClosePrice
    转换线：
    基准线：
    云带上限：
    云带下限：
    迟来线：
    '''
    #获取初始的HA数值
    if len(g.trendList) == 0:
        g.lastNewOpenPrice,g.lastNewClosePrice = computeNewK(stock,short)
        if g.lastNewOpenPrice <= g.lastNewClosePrice:
            g.trendList.append(1)
        else:
            g.trendList.append(-1)
        
    #获取昨日HA数值
    h = attribute_history(stock, mid+longT, '1d', ('open','close','high','low'), None)
    newCloseK = (h['open'][-1] + h['close'][-1] + h['high'][-1] + h['low'][-1]) / 4.0   
    newOpenK  = (g.lastNewOpenPrice + g.lastNewClosePrice) / 2.0
    g.lastNewOpenPrice = newOpenK
    g.lastNewClosePrice = newCloseK
    newHighK = max(newOpenK,newCloseK,h['high'][-1])
    newLowK = min(newOpenK,newCloseK,h['low'][-1])
      
    #计算趋势队列
    if g.lastNewOpenPrice < g.lastNewClosePrice:
        if g.trendList[-1] >= 0:
            g.trendList.append(g.trendList[-1]+1)
        else:
            g.trendList.append(1)
    elif g.lastNewOpenPrice > g.lastNewClosePrice:
        if g.trendList[-1] <= 0:
            g.trendList.append(g.trendList[-1]-1)
        else:
            g.trendList.append(-1)
    else:
        if g.trendList[-1] >= 0:
            g.trendList.append(g.trendList[-1]+1)
        else:
            g.trendList.append(g.trendList[-1]-1)
            
    #计算各种线的指标
    turnLine = (h['high'][-short:].max()+h['low'][-short:].min()) / 2.0
    baseLine = (h['high'][-mid:].max()+h['low'][-mid:].min()) / 2.0
        
    temA = (h['high'][-(mid+short):-mid].max()+h['low'][-(mid+short):-mid].min()) / 2.0
    temB = (h['high'][-longT:-mid].max()+h['low'][-longT:-mid].min()) / 2.0
    cloudUpLine = (temA + temB) / 2.0
        
    cloudDwonLine = (h['high'][0:-mid].max()+h['low'][0:-mid].min()) / 2.0
        
    lateLine = h['close'][-(mid+1)]
    
    #计算现在的价格状态
    if g.trendList[-1] > 0:
        #现在属于轻度上升趋势
        g.stat = 1
        #价格在转换线上方时候，属于中度上升趋势
        if h['close'][-1] >= turnLine:
            g.stat = 2  
        #转换线在基准线上方时候，属于强烈上升趋势
        if turnLine >= baseLine:
            g.stat = 3  
    else:
        #现在属于轻度下降趋势
        g.stat = -1
        #价格在转换线下时候，属于中度下降趋势
        if h['close'][-1] <= turnLine:
            g.stat = -2  
        #转换线在基准线下方时候，属于强烈下降趋势
        if turnLine <= baseLine:
            g.stat = -3 
        
    
    
#买卖函数
def buyOrSell(stock,percent,flag,amount):
    amount = amount * percent
    if flag == 1:
        order_value(stock, amount)
        log.info("Buying %s" % (stock))
    else:
        order_target_value(stock, amount)
        log.info("Selling %s" % (stock))
        
#判断某条线是否穿越K线
def isInK(line,openK,closeK,highK,LowK):
    if (line > openK and line < closeK) or (line < closeK and line > openK):
        return 1
    elif line > LowK and line < highK:
        return 2
    else:
        return 0
        
# 每个单位时间(如果按天回测,则每天调用一次,如果按分钟,则每分钟调用一次)调用一次
def handle_data(context, data):

    for stock in stocks:
        #计算HA数值
        computeHaValue(stock)
        
        # 取得当前的现金
        cash = context.portfolio.cash
        sellAmt = context.portfolio.positions[stock].sellable_amount
        
        #处理需要买的情况

    
            
        #DEBUG 
        #输出各种线指标
        #record(turnLine=turnLine)
        #record(baseLine=baseLine)
        #record(cloudUpLine=cloudUpLine)
        #record(cloudDwonLine=cloudDwonLine)
        #record(lateLine=lateLine)
        record(trend=g.trendList[-1])
        
            
            
 
