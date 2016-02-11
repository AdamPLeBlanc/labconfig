#!/usr/bin/env python
from random import randint
import json

def getTeam():
    return "Team %d" % randint(1,2)

def getBuild():
    if(randint(0,7)):
        return "PTAS_7.%d" % randint(10,21)
    else:
        return "N/A"

sVals = ["Ready for Work","In Progress","Done","Blocked"]
def getStatus():
    if(randint(0,8)):
        return sVals[randint(0,len(sVals)-1)]
    else:
        return "N/A"

actIds = ["KA30124","KA45780","KAA4783"]
def getActivityId():
    if(randint(0,5)):
        return actIds[randint(0,len(actIds)-1)]
    else:
        return "N/A"

if __name__ == "__main__":
    filePath = "bliInfoPath.json"
    bliList = []
    for id in range(1,50):
        tmpBliInfo = ['B-%d' % (1000 + id), \
                      'Test BLI %d' % id, \
                      getTeam(), \
                      getStatus(), \
                      getActivityId(), \
                      getBuild()]
        bliList.append(tmpBliInfo)
    jsonDump = json.dumps(bliList)
    open(filePath,'wb').write(jsonDump)
