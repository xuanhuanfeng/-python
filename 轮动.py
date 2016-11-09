"""
基于韭菜Hurk 的 二八轮动策略修改，谢谢韭菜Hurk 的分享
1、通过 run_daily 指定交易时间
2、股票池支持增加多个股票
3、回测结果黄金ETF、创业板、沪深300一起轮动效果最好
4、增加仓位控制策略，从 10% 开始，减少熊市的回撤
大家如果发现有更好的组合，欢迎随时告诉我。谢谢
                    -- 小兵哥
"""
import talib

def initialize(context):
    #用沪深 300 做回报基准
    set_benchmark('000300.XSHG')

    #设置买卖手续费，万三，最小 5 元
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))

    # 关闭部分log
    log.set_level('order', 'error')
    # 定义全局变量, 保存要操作的证券
    # 去掉了债券，因为引入很多变量，只做了仓位控制。剩余资金，自行线下去买理财产品

    # 定义股票池
    context.stocks = ['518880.XSHG','159915.XSHE','510300.XSHG']
    
    # 初始化
    context.stockPositionsValue = 0
    # 定义股票仓位
    context.stockRatio = 0.1
    context.returns = 0
    context.todayaction = []
    context.lag = 20
    context.oldPosition = 0.0
    context.newPosition = 0.0
    context.message = []
    context.changePositionFlag = 0
    context.beststock = ""
    context.tradeFlag = 0
    context.stoplossFlag = 0
    
    run_daily(fun_check_rebalance,'09:30')

    run_daily(fun_stoploss_policy,'14:00')

    run_daily(fun_buy_policy,'14:00')

    run_daily(fun_buy_beststock, '14:00')

def before_trading_start(context):

    context.todayaction = []
    context.message = []
    context.tradeFlag = 0
    context.returns = 0

    hstocks = history(context.lag,'1d','close',context.stocks,df=False)

    for i in range(len(context.stocks)):
        # 根据昨日 20 天均线，评估当天是否有交易机会
        stock = context.stocks[i]
        price = hstocks[stock][-1]
        ma = talib.SMA(hstocks[stock], 20)[-1]

        if price < ma:
            context.todayaction.append(False)
            context.message.append(stock + " sell all | \n")
        else:
            context.todayaction.append(True)
            context.message.append(stock + " buy in | \n")
    send_message(context.message)

def after_trading_end(context):
    if context.tradeFlag == 1:
        context.tradeFlag == 0
        context.oldPosition = fun_currentPosition(context)

    if context.stoplossFlag == 1:
        context.stoplossFlag = 0
        context.oldPosition = fun_currentPosition(context)
        if context.oldPosition == 0:
            context.returns = 3
            fun_rebalance(context)

# 判断买入股票的策略
def fun_buy_policy(context):
    context.beststock = ""
    context.buystocklist = []
    for i in range(len(context.stocks)):
        if context.todayaction[i] and fun_check_buy(context.stocks[i],context):
            #if fun_check_buy(context.stocks[i],context):
            context.buystocklist.append(context.stocks[i])

    if context.buystocklist != []:
        fun_select_beststock(context)
    else:
        return False

def fun_check_buy(stock,context):
    # 取个股的 n 日均线及现价
    hstocks = history(context.lag,'1d','close',stock,df=False)
    price = history(1,'1m','close',stock,df=False)[stock]

    if price > hstocks[stock][0]:
        return True
    else:
        return False

def fun_select_beststock(context):
    context.beststock = ""
    bestreturn = 0

    hstocks = history(context.lag,'1d','close',context.buystocklist,df=False)
    cstocks = history(1, '1m', 'close', context.buystocklist,df=False)
    for i in range(len(context.buystocklist)):
        stock = context.buystocklist[i]
        pstock = cstocks[stock]
        restock = (pstock - hstocks[stock][0])/hstocks[stock][0]

        if restock > bestreturn:
            context.beststock = context.buystocklist[i]
            bestreturn = restock

    if context.beststock != "":
        fun_sell_betterstock(context)

# 卖掉不是最好的股票
def fun_sell_betterstock(context):
    myholdstock = list(context.portfolio.positions.keys())
    context.newPosition = 0

    # 标识是否是换仓
    context.changePositionFlag = 0

    # 如果已有持仓，清理掉非最佳股票
    for stock in myholdstock:
        if stock != context.beststock:
            context.newPosition = fun_currentPosition(context)
            myStockNewPrice = history(1,'1m','close',stock,df=False)[stock]
            order_target(stock, 0)
            context.changePositionFlag = 1 #标识为换仓

            context.message.append(stock + " sell all | \n")

def fun_buy_beststock(context):
    if context.beststock == "":
        return

    # 检查已有持仓
    myStockAmount = context.portfolio.positions[context.beststock].total_amount
    myStockNewPrice = history(1,'1m','close',context.beststock,df=False)[context.beststock]
    myValue = myStockAmount * myStockNewPrice

    myRatioValue = context.portfolio.portfolio_value * context.stockRatio
    cash = context.portfolio.cash

    # 如果是换仓，等于刚才新的仓位市值
    if context.changePositionFlag == 1:
        buyValue = context.newPosition
    # 开仓，没货代表开仓，按照配额市值买入
    elif myStockAmount == 0:
        buyValue = myRatioValue
    # 加仓，已有货，买入的股票价值 = 额度 - 已有
    else:
        buyValue = myRatioValue - myValue

    buyValue = myRatioValue
    if (buyValue-myValue) > 500:
        order_target_value(context.beststock, buyValue)
        context.message.append("buy stock " + context.beststock + ", " + str(buyValue) + " | \n")
        context.tradeFlag = 1

#判断是否需要卖股票
def fun_stoploss_policy(context):
    context.sellstocklist = []
    for i in range(len(context.stocks)):
        if context.todayaction[i] == False:
            context.sellstocklist.append(context.stocks[i])
        elif fun_check_stoploss(context.stocks[i],context):
            context.sellstocklist.append(context.stocks[i])

    if context.sellstocklist != []:
        fun_sell_action(context)

def fun_check_stoploss(stock,context):
    hstocks = history(context.lag,'1d','close',stock,df=False)
    price = history(1,'1m','close',stock,df=False)[stock]

    if price <= hstocks[stock][0]:
        return True
    else:
        return False

# 卖股票函数，myRatio 指目标股票仓位最终占比
def fun_sell_action(context):
    myholdstock = list(context.portfolio.positions.keys())
    myFlag = 0
    context.stoplossFlag = 0

    for stock in context.sellstocklist:
        if stock in myholdstock:
            order_target(stock, 0)
            myFlag = 1
            context.stoplossFlag = 1
            context.message.append(stock + "sell all | \n")

# 检查是否需要重新平衡股票仓位
def fun_check_rebalance(context):
    stockValue = fun_currentPosition(context) #更新股票市值

    # 没有股票则不判断
    if stockValue == 0:
        return False
    if stockValue > context.oldPosition:
        context.returns = 1
    else:
        context.returns = 2

    deltaValue = abs(stockValue - context.oldPosition)

    if context.oldPosition != 0:
        if deltaValue / context.oldPosition >0.05:
            fun_rebalance(context)

# 重新计算股票比重
def fun_rebalance(context):
    myoldRatio = context.stockRatio
    # 如果正回报，股票最大仓位增加；负回报股票最大仓位减少
    if context.returns == 1:    # 回报 +5%，增加仓位
        context.stockRatio = context.stockRatio * 5
    elif context.returns == 2:  # 回报 -5%，调整仓位
        context.stockRatio = context.stockRatio / 5
    elif context.returns == 3:  # 止损，调整仓位
        context.stockRatio = context.stockRatio / 5

    #股票最大仓位
    if context.stockRatio >= 1:
        context.stockRatio = 1
    #股票最小仓位为 10%
    if context.stockRatio < 0.1:
        context.stockRatio = 0.1
    context.stockRatio = round(context.stockRatio * 100) / 100

    if myoldRatio <= context.stockRatio:
        context.oldPosition = fun_currentPosition(context)

    return None

# 获取实时仓位
def fun_currentPosition(context):
    myNewPosition = 0
    for stock in context.stocks:
        myNewPosition += context.portfolio.positions[stock].total_amount *\
                        history(1,'1m','close',stock,df=False)[stock]
    return myNewPosition