def findMinPoint(y,x):
    yNum = len(y)
    yMin = []
    xMin = []
    for i in range(1,yNum-1):
      if y[i] < y[i-1] and y[i+1] > y[i]:
        yMin.append(y[i])
        xMin.append(x[i])
            
    return yMin,xMin    

    def findMinPoint(y,x,n):
    yNum = len(y)
    yMin = []
    xMin = []
    
    
    if yNum < 2 * n + 1:
        return yMin,xMin
    
    for i in range(n,yNum-n):
        isTop = 1
        for j in range(n):
            if y[i-j-1] <= y[i-j] or y[i+j+1] <= y[i+j]:
                isTop = 0
        if  isTop == 1:   
            yMin.append(y[i])
            xMin.append(x[i])
            
    return yMin,xMin    