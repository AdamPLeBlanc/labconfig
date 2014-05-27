#!/usr/bin/env python

import sys
import os
import datetime
import re
import time
import getopt
from sets import Set

from xml.dom.minidom import Document
from xml.dom .minidom import parse
from xml.dom.minidom import parseString

import threadutil

#define classes to model xml file and store data

class BliFileChange(object):
    def __init__(self,path="",idList=None,createDateFull="",owner=""):
        self.path = path
        self.idList = idList
        if self.idList == None:
            self.idList = []
        self.createDate = createDateFull
        self.owner = owner

    def __str__(self):
        retVal = []
        retVal.append("Path: %s" % self.path.ljust(10))
        retVal.append("Bli IDs: %s " % ','.join(self.idList).ljust(10))
        retVal.append("Date: %s " % self.createDate.ljust(10))
        retVal.append("Owner: %s " % self.owner.ljust(10))
        return '\n'.join(retVal)

    def __eq__(self,other):
        if isinstance(other,BliFileChange):
            return other.path == self.path
        return NotImplemented

    def __hash__(self):
        return hash(self.path)

class BliFileChangeCollection(object):
    def __init__(self,startDate="",endDate=""):
        self.startDate = startDate
        self.endDate = endDate
        self.changeList = {}

    def addFileChange(self,bliFileChange):
        for id in bliFileChange.idList:
            tmpSet = self.changeList.get(id,Set())
            tmpSet.add(bliFileChange)
            self.changeList[id] = tmpSet

    def toXml(self,oStream):
        def getTabs(tNum):
            t = 2
            return ' ' * t * tNum

        oStream.write('<?xml version="1.0" encoding=utf-8" ?>\n')
        oStream.write('<XmlBliFileChangeCollection xmlns:xsi=http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">\n')
        oStream.write('%s<historyStart>%s</historyStart>\n' % (getTabs(1),self.startDate))
        oStream.write('%s<historyEnd>%s</historyEnd>\n' % (getTabs(1),self.endDate))
        oStream.write('%s<backlogItemChanges>\n' % getTabs(1))
        for id, cSet in self.changeList.items():
            oStream.write('%s<item>\n' % getTabs(2))
            oStream.write('%s<key>\n' % getTabs(3))
            oStream.write('%s<string>%s</string>\n' % (getTabs(4),id))
            oStream.write('%s</key>\n' % getTabs(3))
            oStream.write('%s<value>\n' % getTabs(3))
            oStream.write('%s<ArrayOfBacklogItemFileChange>\n' % getTabs(4))
            for c in cSet:
                oStream.write('%s<BacklogItemFileChange>\n' % getTabs(5))
                oStream.write('%s<FullPath>%s</FullPath>\n' % (getTabs(6),c.path))
                oStream.write('%s<AttributeBacklogIds>\n' % getTabs(6))
                for id in c.idList:
                    oStream.write('%s<string>%s</string\n' % (getTabs(7),id))
                oStream.write('%s</AttributeBacklogIds>\n' % getTabs(6))
                oStream.write('%s<CreationDate>%s</CreationDate>\n' % (getTabs(6),c.createDate))
                oStream.write('%s<Owner>%s</Owner>\n' % (getTabs(6),c.owner))
                oStream.write('%s</BacklogItemFileChange>\n' % getTabs(5))
            oStream.write('%s</ArrayOfBacklogItemFileChange>\n' % getTabs(4))
            oStream.write('%s</value>\n' % getTabs(3))
            oStream.write('%s</item>\n' % getTabs(2))
        oStream.write('%s<backlogItemChanges>\n' % getTabs(1))
        oStream.write('%s</XmlBliFileChangeCollection>\n')

    def fromXml(dataSource):
        def getNodeValue(elemList): # return string value of first node in list and an empty string if no value on node
            retVal = ""
            for elem in elemList:
                if elem.firstChild:
                    retVal = elem.firstChild.nodeValue
                break
            return retVal

        if os.path.isfile(dataSource):
            d = parse(dataSource)
        else:
            d = parseString(dataSource)
        retVal = BliFileChangeCollection()
        retVal.startDate = getNodeValue(d.getElementsByTagName('historyStart'))
        retVal.endDate = getNodeValue(d.getElementsByTagName('historyEnd'))
        for bli in d.getElementsByTagName('item'):
            bliId = getNodeValue(bli.getElementsByTagName('key')[0].getElementsByTagName('string'))
            tmpSet = retVal.changeList.get(bliId,Set())
            for fc in bli.getElementsByTagName('BacklogItemFileChange'):
                tmpFc = BliFileChange(getNodeValue(fc.getElementsByTagName('FullPath')),
                    [id.firstChild.nodeValue for id in fc.getElementsByTagName('AttributeBacklogIds')[0].getElementsByTagName('string')],
                    getNodeValue(fc.getElementsByTagName('CreationDate')),
                    getNodeValue(fc.getElementsByTagName('Owner')))
                tmpSet.add(tmpFc)
                retVal.changeList[bliId] = tmpSet
                return retVal

    fromXml = staticmethod(fromXml)

    def __str__(self):
        return 'total ids: %-4d total filechanges: %d' % (len(self.changeList.keys()),sum(map(len,self.changeList.values())))

def GetChanges(cmd,chdir):
    createTags = ["create version","create directory version"]
    retVals = []
    #print r'executing %s in path %s' % (cmd,chdir)
    try:
        os.chdir(chdir)
        stdin,stdout,stderr = os.popen3(cmd)
        for line in stdout:
            evData = line.strip().split(',')
            if evData[0] in createTags:
                path = '/'.join(['',chdir.split('/')[-1],evData[1]])
                idAttr = evData[-1]
                idList = re.findall(r'[BD]-\d+',idAttr) or ['N/A']
                retVals.append(BliFileChange(path,idList,evData[2],evData[3]))
    except OSError:
        print 'could not change to directory %s' % chdir

    return retVals

def usage():
    usage = []
    usage.append('--help          print usage')
    usage.append('--refresh       create new xml file with optional date. ex 2014-01-14T00:00:00')

    print '\n'.join(usage)
    sys.exit(2)

def main(argv):
    dateFmt = '%Y-%m-%dT%H:%M:%S'
    vobPrefix = "/vobs/"
    ccCmdTemplate = r'cleartool lshistory -nco -recurse -fmt %s -since %s -branch %s'
    fmtTemplate = r'"%e,%Xn,%d,%Fu,%[Change_ID]a\n"'
    branches = ["sprint_int","r14_bugfix","r15_bugfix_030514"]
    vobs =["PTAS","PTAS_tools","CDS/common_graphics","CDS/common_utils","NGT/SIM",
        "PTD_Docs","common_limited","CDS/common_dp","CDS/common_libs"]
    mergeFilePath = "c:\mergedFileData.xml"
    refresh = False
    sinceDate = None
    verbose = True

    #parse arguments
    try:
        opts,args = getopt.getopt(argv,'h',['help','refresh='])
    except getopt.GetoptError:
        print 'not all arguments were passed in correctly\n'
        usage()

    for opt,arg in opts:
        if opt in ('-h','--help'):
            usage()
        elif opt == '--refresh':
            refresh = True
            try:
                time.strptime(arg,dateFmt) #checks date format
                sinceDate = arg
            except ValueError:
                pass

    #configure date at which to query cc and to figure out if to refresh whole xml file
    todaysDate = datetime.datetime.today().strftime(dateFmt)
    if not refresh or (refresh and not sinceDate):
        print 'reading merge history from %s' % mergeFilePath
        startTime = time.time()
        fChanges = BliFileChangeCollection.fromXml(mergeFilePath)
        if refresh:
            sinceDate = fChanges.startDate
        else:
            sinceDate = fChanges.endDate
        print 'finished reading.. took %.2f seconds' % (time.time() - startTime)
    if refresh:
        fChanges = BliFileChangeCollection(sinceDate,todaysDate)

    # put together list of cmds to feed to threads
    cmdItems = []
    startTime = time.time()
    print "starting to collect merge history from %s" % sinceDate

    for vob in vobs:
        newPath = vobPrefix + vob
        if os.path.isdir(newPath):
            for branch in branches:
                cmdItems.append(threadutil.CmdItem(GetChanges,[ccCmdTemplate % (fmtTemplate,sinceDate,branch),newPath]))
        else:
            print '%s is not a valid path' % newPath

    #kick off threads
    results = []
    tMgr = threadutil.ThreadManager(cmdItems,results=results,verbose=verbose)
    tMgr.run()

    #add all the changes to the change collection. 
    #the results list ends up being a list of lists with the FC items in them

    fcList = [item for resultList in results for item in resultList]
    print 'found %d filechanges, adding non duplicate results to filechange collection' % len(fcList)

    print 'original fc info: %s' % fChanges
    for fc in fcList:
        fChanges.addFileChange(fc)
    #updated enddate in collection
    fChanges.endDate = todaysDate
    print 'new fc info    : %s' % fChanges

    #write chnages to xml file
    try:
        outFile = open(mergeFilePath,'wb')
        fChanges.toXml(outFile)
    except IOError:
        print 'Do not have write permissions for %s' % mergeFilePath

    print 'done: compute time - %.2f' % (time.time() - startTime)

if __name__ == "__main__":
    main(sys.argv[1:])

