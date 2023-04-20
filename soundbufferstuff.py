import argparse
import mmap
import time
import numpy
import numpy as np
import math
import cv2
import random

MAXFPS = 30

parser = argparse.ArgumentParser(description='Play a buffer')
parser.add_argument('-noplayback',action='store_true',help='Connect to Jack Playback')

args = parser.parse_args()
noplayback = args.noplayback

ds = 4
# N = int((iend-iostart)//ds)
N = 512*512
n = math.floor(math.sqrt(N))
n = min(n,1024)



arr  = numpy.zeros(n*n,dtype=numpy.int32)
loop  = numpy.zeros(n*n,dtype=numpy.int32)
loop_len = 0
buff = numpy.zeros(n*n,dtype=numpy.float32)
last = numpy.zeros(n*n,dtype=numpy.int32)
show = numpy.zeros((n, n),dtype=numpy.uint8)
data = numpy.zeros((n, n))

screen_name = "sacramentoaudiowaffles"
fullscreen = False

def doFullscreen():
    global fullscreen
    if not fullscreen:
        cv2.setWindowProperty(screen_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        fullscreen = True
    else:
        cv2.setWindowProperty(screen_name, cv2.WND_PROP_FULLSCREEN, 0)
        fullscreen = False


silence = 0
handlers = dict()

def zero_offset():
    global off
    global iostart
    off = 0
    iostart = istart + off
def reduce_offset(m=10):
    global off
    global iostart
    off = max(0, off - m*4*n)
    iostart = istart + off
def increase_offset(m=10):
    global off
    global iostart
    off = max(0, off + m*4*n)
    iostart = istart + off
    print(iostart)
def increase_offset_alot():
    increase_offset(m=100)
def reduce_offset_alot():
    reduce_offset(m=100)
def silence_output():
    global silence
    silence = 10

def random_box(maxw=100):
    pt = (random.randint(0, n-1),random.randint(0, n-1))
    pt2 = (min(n-1,random.randint(pt[0], pt[0]+maxw)),
           min(n-1,random.randint(pt[1], pt[1]+maxw)))
    return [pt,pt2]

def random_box_cb(maxw):
    global the_rectangle
    global dirty
    dirty = True
    the_rectangle = random_box(maxw)

def random_small_box():
    random_box_cb(100)
def random_medium_box():
    random_box_cb(300)
def random_big_box():
    random_box_cb(900)
def middle_box():
    global the_rectangle
    global dirty
    pt = (0,int(n/3))
    pt2 = (n-1,int(2*n/3))
    dirty = True
    the_rectangle = [pt,pt2]

def scale_the_rectangle(scale):
    global the_rectangle
    global dirty
    w = the_rectangle[1][0] - the_rectangle[0][0]
    h = the_rectangle[1][1] - the_rectangle[0][1]
    diffw = int(w*(scale-1.0)/2)
    diffh = int(h*(scale-1.0)/2)
    pt1 = (min(n,max(0,the_rectangle[0][0] - diffw)),
           min(n,max(0,the_rectangle[0][1] - diffh)))
    pt2 = (min(n,max(0,the_rectangle[1][0] + diffw)),
           min(n,max(0,the_rectangle[1][1] + diffh)))
    the_rectangle = [pt1,pt2]
    dirty = True

for i in range(1,10):
    handlers[48+i] = lambda i=i: random_box_cb(100*i)
#handlers[49] = handlers[50] = handlers[51] = random_small_box
#handlers[52] = handlers[53] = handlers[54] = random_medium_box
#handlers[55] = handlers[56] = handlers[57] = random_big_box
handlers[48] = middle_box
# 61 increase size of box
handlers[61] = lambda: scale_the_rectangle(1.1)
# 45 decrease size of box
handlers[45] = lambda: scale_the_rectangle(0.9)

# handlers[82] = reduce_offset
# handlers[82] = reduce_offset_alot
# handlers[85] = reduce_offset_alot
# handlers[84] = increase_offset
# handlers[84] = increase_offset_alot
# handlers[86] = increase_offset_alot

# home 
# handlers[80] = zero_offset
handlers[32] = silence_output

# laser pointer
handlers[9]  = middle_box
handlers[10] = random_big_box


dirty = False
cv2.namedWindow(screen_name, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO )
def handle_keys():
    global fullscreen
    global handlers
    global dirty
    global silence
    silence -= 1
    k = cv2.waitKey(1000//MAXFPS) & 0xff
    if k == 27:
        return True
    elif k == ord('f'):
        doFullscreen()
    else:
        if k in handlers:            
            handlers[k]()
            dirty = True
        elif k!=255:
            print(k)
    return False

# get our jack client
import jackclient
the_rectangle =  [(0,0),(n,n)]
temp_rectangle = [(0,0),(n,n)]

def handle_loop(rectangle):
    """ copy to buffer """
    global loop
    global loop_len
    nr = ((min(rectangle[0][0],rectangle[1][0]),min(rectangle[0][1],rectangle[1][1])),
          (max(rectangle[0][0],rectangle[1][0]),max(rectangle[0][1],rectangle[1][1])))
    width = nr[1][0] - nr[0][0]
    height = nr[1][1] - nr[0][1]
    rectsize = width*height
    loop_len = rectsize
    if loop_len == 0:
        None
    else:
        loop[0:rectsize] = arr.reshape((n,n))[nr[0][0]:nr[1][0],nr[0][1]:nr[1][1]].reshape((rectsize))
        

cbi_l = 0
def cb(self, frames, count):
    global cbi_l
    if silence > 0 or loop_len == 0:
        buff[0:frames] = 0
    else:
        samples = 0
        start = cbi_l 
        indices = numpy.arange(cbi_l, start+frames) % loop_len
        cbi_l = (start+frames) % loop_len
        buff[0:frames] = loop[indices]
    return (buff[0:frames] % 1024)/1024.0

def cb_no_loop(self, frames, count):
    global arr
    global n    
    index = count % (n*n)
    if (index + frames >= n*n):
        remaining = (index + frames) % (n*n)
        off1 = n*n - index
        buff[0:off1] = arr[index:index+off1]
        buff[off1:off1+remaining] = arr[0:remaining]
    else:
        buff[0:frames] = arr[index:index+frames]
    return (buff[0:frames] % 1024)/1024.0

import os, pwd, grp

print("Start Jack Client")
#jc = jackclient.Jackclient(cb=cb,name="pyjack",servername="default")
jc = jackclient.Jackclient(cb=cb,name="sbstuff",servername="default")
event = jc.start()
if not noplayback:
    jc.connect_to_output()



def first_corner(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        temp_rectangle[0] = (x,y)
        temp_rectangle[1] = (x,y)
        cv2.setMouseCallback(screen_name, second_corner)
        
def second_corner(event, x, y, flags, param):
    temp_rectangle[1] = (x,y)
    if event == cv2.EVENT_LBUTTONUP:
       temp_rectangle[1] = (x,y)
       if temp_rectangle[0][1] > temp_rectangle[1][1]:
           temp_rectangle[0], temp_rectangle[1] = temp_rectangle[1], temp_rectangle[0]
       the_rectangle[0] = temp_rectangle[0]
       the_rectangle[1] = temp_rectangle[1]
       handle_loop(the_rectangle)
       cv2.setMouseCallback(screen_name, first_corner)

            # cv2.rectangle(bgimage, (x,y), (x+2,y+2), (0, 255, 0), 2)
            #cv2.imshow(screen      _name, bgimage)


cv2.setMouseCallback(screen_name, first_corner)

# refactor this so the animate calls it
# https://matplotlib.org/examples/animation/dynamic_image.html
#fd.seek(iostart)
#last = fd.read(iend - iostart)
#arr[0:n*n] = numpy.fromfile(fd, dtype=numpy.int32, count=n*n)

_positions = np.arange(n*n)
def next_frame(arr,last,n,t):
    arr[0:n*n] = 255*np.sin(2*3.14*(arr/255.0 + _positions/(n*n)))[0:n*n]

class BuffStructure:
    def __init__(self,arr):
        self.arr = arr
        self.init_arr()
    def init_arr(self):
        """ hook """
    def get_arr(self):
        return self.arr
    def next_frame(self,arr,last,n,t):
        raise Exception("Unfinished")
    def assign_show_frame(self,arr,show,n):
        show[0:n,0:n] = (arr).reshape(n,n)

class Bars(BuffStructure):
    def init_arr(self):
        self.circle_init()
    def circle_init(self):
        x = np.linspace(-5, 5, n)
        y = np.linspace(-5, 5, n)
        xx, yy = np.meshgrid(x, y)
        z = np.sin(xx**2 + yy**2) / (xx**2 + yy**2)
        self.arr[0:n*n] = 255*z.reshape(n*n)
        self.xxx = xx.reshape(n*n)
        self.yyy = yy.reshape(n*n)
    def next_frame(self,arr,last,n,t):
        arr[0:n*n] = last[0:n*n] + self.xxx - self.yyy

class Shift(BuffStructure):
    def next_frame(self,arr,last,n,t):
        arr[0] = 128*np.sin(2*np.pi*t/100)
        arr[1:n*n] = arr[0:(n*n)-1]

import scipy.ndimage
class TMover(BuffStructure):
    def init_arr(self):
        arr[0:n*n] = np.random.random(n*n)*np.random.randint(0,65535,n*n)
        sigma = [15.0,45.0]
        arr[0:n*n] = scipy.ndimage.filters.gaussian_filter(arr.reshape(n,n), sigma, mode='constant').reshape(n*n)
    def next_frame(self,arr,last,n,t):
        arr[0:n*n] = arr[0:n*n] - t%33

class UnknownSound(BuffStructure):
    def next_frame(self,arr,last,n,t):
        arr[0:n*n] = 255*np.sin(2*3.14*(arr/255.0 + _positions/(n*n)))[0:n*n]
rule60 =  [0,0,1,1,1,1,0,0]
rule73i =  [0,1,0,0,1,0,0,1]
rule73 =  [1,0,0,1,0,0,0,1]
rule193i = [1,1,0,0,0,0,0,1]
rule193 = [1,0,0,0,0,0,1,1]
# rule103 = [0,1,1,0,0,1,1,1]
rule103 = [1,1,1,0,0,1,1,0]

goodrules = [rule60,rule73i,rule73,rule193i,rule193,rule103]

class CellularAutomata(BuffStructure):
    def set_table(self,table=rule73):
        self.table = table
        self.ntable = numpy.array(table,dtype=np.int32).reshape(2,2,2)
    def init_arr(self):
        self.fill = 1
        self.lastrow = np.zeros(n+2,dtype=np.int32)
        self.row = 0
        self.set_table()
        self.arr[0:n*n] = self.fill
        self.arr[n//2] = 1 * (not self.fill)
        self.arr[0:n*n] = np.random.randint(0,2,n*n)
        for i in range(n):
            self._next_frame(self.arr,None,n,i)
    def next_frame(self,arr,last,n,t):
        #for j in range(5):
        self._next_frame(arr,last,n,t)
        if numpy.random.rand() > 0.995:
            i = self.row
            if i >= n:
                i = n-1
                #arr[i*n:i*n+n] = np.random.randint(0,2,n) * np.random.randint(0,2,n)
            arr[i*n:i*n+n] = np.random.randint(0,2,n) * np.random.randint(0,2,n)
            self.set_table(random.choice(goodrules))
    def _next_frame(self,arr,last,n,t):
        lastrow = self.lastrow
        lastrow[0] = self.fill
        lastrow[n+1] = self.fill
        if self.row < (n-1):
            i = self.row%n
            lastrow[1:n+1] = arr[i*n:i*n+n]
            arr[((i+1)%n)*n:((i+1)%n)*n+n] = 255*self.ntable[1*(lastrow[0:n]>0),1*(lastrow[1:n+1]>0),1*(lastrow[2:n+2]>0)]
        else:
            lastrow[1:n+1] = arr[n*(n-1):n*n]
            arr[0:(n-1)*n] = arr[n:n*n]
            arr[n*(n-1):n*n] = 255*self.ntable[1*(lastrow[0:n]>0),1*(lastrow[1:n+1]>0),1*(lastrow[2:n+2]>0)]
        self.row += 1
        

    def assign_show_frame(self,arr,show,n):
        show[0:n,0:n] = (arr).reshape(n,n)
        
        
bstruct_t = CellularAutomata
bstruct = bstruct_t(arr)
#bstruct.set_table(rule73)

t = 0
# per frame
while True:
    # get our frame as arr
    # fd.seek(iostart)
    # arr[0:n*n] = numpy.fromfile(fd, dtype=numpy.int32, count=n*n)
    bstruct.next_frame(arr,last,n,t)
    dirty = True
    # get a difference
    diff = numpy.sum(arr-last)
    if (diff != 0):
        dirty = True
    # get the UI picture
    #show[0:n,0:n] = (arr).reshape(n,n)
    bstruct.assign_show_frame(arr,show,n)
    # loop copying
    #if dirty:
    handle_loop(the_rectangle)
    #    dirty = False
    # draw rectangles
    cv2.rectangle(show, temp_rectangle[0], temp_rectangle[1], 127+64, 2)
    cv2.rectangle(show, the_rectangle[0], the_rectangle[1], 255, 2)
    cv2.imshow(screen_name,show)

    if handle_keys():
        break
    # last, arr = (arr, last)
    last[0:n*n] = arr[0:n*n]
    t += 1
