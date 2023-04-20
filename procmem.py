import argparse
import mmap
import time
import numpy
import math
import cv2
import random

parser = argparse.ArgumentParser(description='Read the stack and heap of a process')
parser.add_argument('pid', help='PID of process to read')
parser.add_argument('-grep', default="stack", help='Stack or heap')
parser.add_argument('-off', default=0, help='Offset')
parser.add_argument('-noplayback',action='store_true',help='Connect to Jack Playback')

args = parser.parse_args()
noplayback = args.noplayback
pid = int(args.pid)
filename = "/proc/{}/maps".format(str(pid))
mem_filename = "/proc/{}/mem".format(str(pid))
print("Filename %s" % filename)
lines = open(filename).readlines()
match = "[%s]" % args.grep
stacklines = [l for l in lines if match in l]
print(stacklines)
s_start, s_end = stacklines[0].split(" ")[0].split("-")
print("%s - %s" % (s_start, s_end))
istart, iend = (int(s_start,16), int(s_end, 16))
off = int(args.off)
iostart = istart + off
print("%s - %s" % (iostart, iend))
print("Opening memory now")
import mmap
fd = open(mem_filename,'rb')
#mm = mmap.mmap(fd.fileno(),0, mmap.MAP_SHARED, mmap.PROT_READ)
#print("Mem mapped!")
#print(mm[istart:istart,istart+16])
ds = 4
N = int((iend-iostart)//ds)
n = math.floor(math.sqrt(N))
n = min(n,1024)
arr  = numpy.zeros(n*n,dtype=numpy.int32)
loop  = numpy.zeros(n*n,dtype=numpy.int32)
loop_len = 0
buff = numpy.zeros(n*n,dtype=numpy.float32)
last = numpy.zeros(n*n,dtype=numpy.int32)
show = numpy.zeros((n, n),dtype=numpy.uint8)
data = numpy.zeros((n, n))

screen_name = "procmem"
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
handlers[82] = reduce_offset_alot
handlers[85] = reduce_offset_alot
# handlers[84] = increase_offset
handlers[84] = increase_offset_alot
handlers[86] = increase_offset_alot

# home 
handlers[80] = zero_offset
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
    k = cv2.waitKey(1000//60) & 0xff
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

# Tamás https://stackoverflow.com/a/2699996 Stackoverflow
# Dr Gavin Baker   http://antonym.org/2005/12/dropping-privileges-in-python.html
def drop_privileges(uid_name='nobody', gid_name='nogroup'):
    if os.getuid() != 0:
        # We're not root so, like, whatever dude
        return
    # Get the uid/gid from the name
    running_uid = pwd.getpwnam(uid_name).pw_uid
    running_gid = grp.getgrnam(gid_name).gr_gid
    # Remove group privileges
    os.setgroups([])
    # Try setting the new uid/gid
    os.setgid(running_gid)
    os.setuid(running_uid)
    # Ensure a very conservative umask
    old_umask = os.umask(0o77)

# we have to give up our root because we cannot connect jack otherwise.
# also, wouldn't it be safer that way?
print("BYE ROOT")
drop_privileges(uid_name='hindle1', gid_name='hindle1')

print("Start Jack Client")
jc = jackclient.Jackclient(cb=cb,name="pyjack",servername="default")
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
fd.seek(iostart)
#last = fd.read(iend - iostart)
arr[0:n*n] = numpy.fromfile(fd, dtype=numpy.int32, count=n*n)
while True:
    # print("[%s]" % x)
    fd.seek(iostart)
    arr[0:n*n] = numpy.fromfile(fd, dtype=numpy.int32, count=n*n)
    diff = numpy.sum(arr-last)
    # data[0:n,0:n] = (arr - last).reshape(n,n)
    # data[0:n,0:n] = (arr).reshape(n,n)
    show[0:n,0:n] = (arr).reshape(n,n)
    if dirty:
        handle_loop(the_rectangle)
        dirty = False
    # draw rectangles
    cv2.rectangle(show, temp_rectangle[0], temp_rectangle[1], 127+64, 2)
    cv2.rectangle(show, the_rectangle[0], the_rectangle[1], 255, 2)
    cv2.imshow(screen_name,show)

    if handle_keys():
        break
    last, arr = (arr, last)

