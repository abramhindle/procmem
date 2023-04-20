#!/usr/bin/env python3
# Copyright (c) 2019 Abram Hindle
# Torn from Matthias Geier.  https://jackclient-python.readthedocs.io/en/0.4.0/examples.html MIT LICENSE
# Copyright (c) 2014-2016 Matthias Geier
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""Create a JACK client that calls numpy for buffers

This is somewhat modeled after the "thru_client.c" example of JACK 2:
http://github.com/jackaudio/jack2/blob/master/example-clients/thru_client.c

"""
import sys
import signal
import os
import jack
import threading
import numpy
import math

def random_cb(self,frames,counter):
    return 0.1*numpy.random.random_sample(frames)

def default_cb(self,frames,counter):
    print(counter/256)
    return 0.1*numpy.sin(2*440.0*numpy.pi * numpy.arange(counter,counter+frames)/44100.0)

class Jackclient:
    def __init__(self,cb=None,name="pyjack",servername=None):
        self.clientname = name
        self.servername = None
        self.client = jack.Client(self.clientname, servername=self.servername)
        self.counter = 0
        if cb is None:
            self.cb = default_cb
        else:
            self.cb = cb

    def connect_to_output(self):
        client = self.client
        playback = client.get_ports(is_physical=True, is_input=True)
        if not playback:
            raise RuntimeError('No physical playback ports')
        for src, dest in zip(client.outports, playback):
            client.connect(src, dest)
            
    def start(self):
        client = self.client
        if client.status.server_started:
            print("JACK server started")
        if client.status.name_not_unique:
            print("unique name {0!r} assigned".format(client.name))
        self.event = threading.Event()
        client.set_process_callback(self.make_process_callback())
        client.set_shutdown_callback(self.make_shutdown_callback())
        for number in 1, 2:
            client.outports.register("output_{0}".format(number))
        self.client.activate()
        return self.event
        
    def make_shutdown_callback(self):
        event = self.event
        def shutdown(status, reason):
            print("JACK shutdown!")
            print("status:", status)
            print("reason:", reason)
            event.set()
        return shutdown

    def make_process_callback(self):
        client = self.client
        numpy_cb = self.cb
        def process(frames):
            assert frames == client.blocksize
            sample = numpy_cb(self,frames,self.counter).astype(numpy.float32)
            self.counter += frames
            for o in client.outports:
                o.get_buffer()[:] = memoryview(sample)# sample.tobytes()
        return process

    def event_loop(self):
        client = self.client
        event = self.event
        with client:
            print("Press Ctrl+C to stop")
            try:
                print("Event.wait before")
                event.wait()
                print("Event.wait after")
            except KeyboardInterrupt:
                print("\nInterrupted by user")

if __name__ == "__main__":
    jc = Jackclient(cb=default_cb)
    event = jc.start()
    #jc.connect_to_output()
    jc.event_loop()
    
