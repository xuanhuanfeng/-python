import numpy as np
import pandas as pd

def zuliValue(x,y,v):
    highSum = 0
    totalSum = 0
    lag = len(y)
    base = np.log(lag+1)
    price = pd.series(y,x)
    price.sort()
    y = price.values
    x = list(price.index)
    
    for i in range(lag):
        if y[i] != y[-1]:
            if i != 0 and y[]
            tmp = v[i] * np.log(1.0/np.abs(y[i]-y[-1])*y[-1]) * (np.log(x[i]+1)/base)
            totalSum += tmp
        
        if y[i] > y[-1]:
            highSum +=  tmp

    if totalSum != 0:
        result = highSum/totalSum
    else:
        result = 0
    

    return x[i],result

def findEasyWay(xs,ys,vs):
    lag = 120
    yNum = len(ys)
    x = []
    y = []

    for i in range(lag,yNum,5):
        x1,y1 = zuliValue(xs[i-lag:i],ys[i-lag:i],vs[i-lag:i])
        x.append(x1)
        y.append(y1)

    return np.array(x),np.array(y)

def drawColor(x,y,ys):
    x1 = []
    y1 = []
    x2 = []
    y2 = []
    x3 = []
    y3 = []
    yNum = len(y)

    for i in range(yNum):
        if y[i]<0.5:
            x1.append(x[i])
            y1.append(ys[i])
        elif y[i]<0.9 and y[i] >= 0.5:
            x2.append(x[i])
            y2.append(ys[i])
        elif y[i]>=0.9:
            x3.append(x[i])
            y3.append(ys[i])
    
    return np.array(x1),np.array(y1),np.array(x2),np.array(y2),np.array(x3),np.array(y3)