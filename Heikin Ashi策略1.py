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
    # 初始化前天的HA开盘价和收盘价
    g.lastNewOpenPrice,g.lastNewClosePrice = computeNewK(stocks[0],52)

    
#买卖函数
#def buyOrSell(stock,

# 每个单位时间(如果按天回测,则每天调用一次,如果按分钟,则每分钟调用一次)调用一次
def handle_data(context, data):

    for stock in stocks:
        #计算昨天的HA数值
        h = attribute_history(stock, 78, '1d', ('open','close','high','low'), None)
        newCloseK = (h['open'][-1] + h['close'][-1] + h['high'][-1] + h['low'][-1]) / 4.0   
        newOpenK  = (g.lastNewOpenPrice + g.lastNewClosePrice) / 2.0
        g.lastNewOpenPrice = newOpenK
        g.lastNewClosePrice = newCloseK
        newHighK = max(newOpenK,newCloseK,h['high'][-1])
        newLowK = min(newOpenK,newCloseK,h['low'][-1])
        
        
        #计算各种线的指标
        turnLine = (h['high'][-9:].max()+h['low'][-9:].min()) / 2.0
        baseLine = (h['high'][-26:].max()+h['low'][-26:].min()) / 2.0
        
        temA = (h['high'][-35:-26].max()+h['low'][-35:-26].min()) / 2.0
        temB = (h['high'][-52:-26].max()+h['low'][-52:-26].min()) / 2.0
        cloudUpLine = (temA + temB) / 2.0
        
        cloudDwonLine = (h['high'][0:-26].max()+h['low'][0:-26].min()) / 2.0
        
        lateLine = h['close'][-27]
        
        #输出各种线指标
        record(turnLine=turnLine)
        record(baseLine=baseLine)
        record(cloudUpLine=cloudUpLine)
        record(cloudDwonLine=cloudDwonLine)
        record(lateLine=lateLine)
        
        #输出验证信息
        log.info("openPrice: %f,highPrice: %f,lowPrice: %f,closePrice: %f",newOpenK,newHighK,newLowK,newCloseK)
        if newCloseK >= newOpenK:
            log.info("红")
        else:
            log.info("绿")
        
        # 取得当前的现金
        cash = context.portfolio.cash

        if turnLine < baseLine and newCloseK < newOpenK and context.portfolio.positions[stock].sellable_amount > 0:
            # 卖出所有股票,使这只股票的最终持有量为0
            order_target(stock, 0)
            # 记录这次卖出
            log.info("Selling %s" % (stock))
        elif turnLine > baseLine and newCloseK >= newOpenK and cash > 0:
            # 用所有 cash 买入股票
            order_value(stock, cash)
            # 记录这次买入
            log.info("Buying %s" % (stock))
            
            
 
