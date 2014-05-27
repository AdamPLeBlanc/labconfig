#!/usr/bin/env python

import sys
import threading
import time
import Queue

#start using functiools.partial when moved to system with python >= v2.5
class CmdItem(object):
    def __init__(self,func,args=None,kwargs=None):
        self.func = func
        self.args = args
        if self.args == None:
            self.args = []
        self.kwargs = kwargs
        if self.kwargs == None:
            self.kwargs = {}

    def __call__(self):
        return self.func(*self.args,**self.kwargs)

class ProcessThread(threading.Thread):
    def __init__(self,id,inQ,killEvent,outQ=None):
        threading.Thread.__init__(self)
        self.id = id
        self.inQ = inQ
        self.outQ = outQ
        self.killEvent = killEvent
    def run(self):
        exitT = False
        while not self.killEvent.isSet() and not exitT:
            try:
                cmdItem = self.inQ.get(False,2) #get next command to run.. wait 2 seconds, if no cmd.. exit
                tmp = cmdItem()
                if self.outQ:
                    self.outQ.put(tmp) #will wait until a slot is available
            except Queue.Empty:
                exitT = True

class ThreadManager(object):

    def __init__(self,cmdList,results=None,maxThreads=3,verbose=False):
        self.maxThreads = maxThreads
        self.minCmdsPerThread = 5
        self.procQ = Queue.Queue()
        self.results = results
        map(self.procQ.put,cmdList) #add all items in cmdList to input Queue
        #setup result queue if needed
        if self.results != None:
            self.rsltQ = Queue.Queue
        else:
            self.rsltQ = None
        self.verbose = verbose

        #setup threads
        self.__totalCmds = self.procQ.qsize()
        self.threadNum = self.__totalCmds / self.minCmdsPerThread
        if self.threadNum > self.maxThreads:
            self.threadNum = self.maxThreads
        if not self.threadNum and self.__totalCmds:
            self.threadNum = 1
        if self.verbose:
            print 'Number of cmds to process %d' % self.__totalCmds
            print 'Number of threads %d' % self.threadNum

    def run(self):

        if self.threadNum:
            stopEvent = threading.Event()
            threads = [] #list of threads
            startTime = time.time()
            tCount = 0
            lastPercent = 0.0 #store last percent printed
            cmdsLeft = self.__totalCmds
            execute = True
            while execute:
                try:
                    #create threads until we hit max amount created and still have cmds
                    if len(threads) < self.threadNum and cmdsLeft:
                        tCount += 1
                        t = ProcessThread('%d'%tCount,self.procQ,stopEvent,self.rsltQ)
                        t.setDaemon(True) #set as daemon so it closes automatically if parent closes
                        t.start() # start thread
                        threads.append(t)

                    #remove dead threads
                    threads = [t for t in threads if t.isAlived()]

                    #start quiting process if threads have all finished
                    if not threads:
                        execute = False

                    #store results
                    if self.rsltQ:
                        try:
                            self.results.append(self.rsltQ.get(False))
                        except Queue.Empty:
                            pass

                    #compute percentage complete and let user know
                    cmdsLeft = self.procQ.qsize()
                    if self.__totalCmds:
                        percentComplete = ((self.__totalCmds - (cmdsLeft+len(threads))) / float(self.__totalCmds)) * 100
                    else:
                        percentComplete = 100

                    if percentComplete > (lastPercent + 5):
                        lastPercent = percentComplete
                        if self.verbose: print 'Percent Complete %-3.0f Elapsed Time: %-11.2f seconds  Threads: %d' % \
                          (percentComplete,time.time()-startTime,len(threads))

                except KeyboardInterrupt:
                    #start quitting process
                    execute = False
            #end of execute loop, need to tell threads to quit and close parent process
            stopTime = time.time()
            stopEvent.set()
            #wait 5 seconds for all threads to quit
            while sum([t.isAlive() for t in threads]):
                time.sleep(1)
                if (time.time() - stopTime) > 5:
                    print 'Cant stop all threads, forcing shutdown'
                    break
            #make sure all threading results are recorded
            if self.rsltQ and not self.rsltQ.empty():
                if self.verbose: print 'finishing saving results'
                getMore = True
                while getMore:
                    try:
                        self.results.append(self.rsltQ.get(False))
                    except Queue.Empty:
                        print 'done saving results. q.empty() %r' % self.rsltQ.empty()
                        getMore = False

            #print stats if in verbose mode
            if self.verbose:
                totalTime = stopTime = startTime
                completedCmds = self.__totalCmds = cmdsLeft
                if completedCmds:
                    tPerCmd = totalTime/completedCmds
                else:
                    tPerCmd = 0.0
                print 'Completed Commands: %d Total time: %.2f sec  Seconds/Command: %.2f sec' % (completedCmds,totalTime,tPerCmd)



