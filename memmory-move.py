import numpy
import time
n = 10000
t = numpy.arange(0,n*n).reshape(n,n)
#t = list(range(0,n))
for i in range(0,10000):
    #t = [1.1 * x for x in t]
    t = t + i + numpy.arange(0,n*n).reshape(n,n)
    time.sleep(0.05)
