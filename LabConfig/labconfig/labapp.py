#!/usr/bin/env python
import sys
import json
import re
import os
from datetime import datetime

mainTemplate ='''
<html>
<head>
    <link rel="stylesheet" type="text/css" href="static/style.css">
    <title>Lab Config</title>
</head>
<body>
    <div class="accent">
        <ul class="menu">
            <li class="menu"><a class="menu" href="#labConfig">Lab Config</a></li>
            <li class="menu"><a class="menu" href="#buildStatus">Build Status</a></li>
        </ul>
    </div>
        %(Body)s
    <div class="accent">
        last updated %(Date)s
    </div>
</body>
</html>'''

configPath = "labConfig.json"
infoCmdLst = None
ipLst = None

def wrapElement(tag,content,**attrs):
    #import pdb; pdb.set_trace()
    retVal = ''
    attrStr = ''
    if attrs:
        attrStr = ' %s' % ' '.join(['%s=%s' %(key,val) for key, val in attrs.items()])
    tmplt = "<%s%s>%s</%s>"
    if re.search('[\r\n]',content):
        content = '\n  %s\n' % '\n  '.join(content.splitlines())
    
    retVal = tmplt % (tag,attrStr,content,tag)
    #import pdb;pdb.set_trace()
    return str(retVal)

def wrapRow(content,**attrs):
    return wrapElement('tr',content,**attrs)

def execCmd(cmd,ipAddr):
    #import pdb;pdb.set_trace()
    cmd = cmd % ipAddr
    retVal = os.popen(cmd).read()
    return [map(str.strip,line.split(':')) for line in retVal.splitlines() if line]

def getSubSystemRowData(ssName,*trainerCmdInfo):
    cmdRetVals = {}
    oLst = []
    cmd = infoCmdLst.get(ssName,'')
    ips = ipLst.values()
    cntr = -1
    for sysInfo in ips: # returns dict of subsystem ip addresses for each trainer
        ip = sysInfo[ssName]
        cntr += 1
        for i in execCmd(cmd,ip):
            if i[0] not in oLst:
                oLst.append(i[0])
            tmpLst = cmdRetVals.get(i[0],['']*len(ips))
            tmpLst[cntr] = i[1]
            cmdRetVals[i[0]] = tmpLst
    rowItems = []
    for item in oLst:
        tmpList = []
        tmpList.append(wrapElement('td',item,**{'class':'"dataHdr"'}))
        tmpList += [wrapElement('td',i,**{'class':'"data"'}) for i in cmdRetVals[item]]
        rowItems.append(wrapRow('\n'.join(tmpList)))

    return '\n'.join(rowItems)

def getCSS():
    return open('templates/style.css','rb').read()

def generateLabConfigHtml():
    #import pdb; pdb.set_trace()
    tblContent = []
    trainers = ipLst.keys()
    #add column headers
    tblContent.append(wrapRow('\n'.join([wrapElement('td','',**{'class':'"colHdr"'})]+
        [wrapElement('th',val,**{'class':'"colHdr"'}) for val in trainers])))
    #for each trainer get lab config info for each subsystem
    for ss, cmdInfo in infoCmdLst.items():
        tblContent.append(wrapRow(wrapElement('td',ss,**{'class':'"lngRow"','colspan':'100%'})))
        tblContent.append(getSubSystemRowData(ss))
    #import pdb;pdb.set_trace()
    body = mainTemplate % {"Body":wrapElement('div',wrapElement('table','\n'.join(tblContent))),"Date":datetime.today().strftime('%b-%d-%Y @ %H:%M:%S')}

    return body

def resolve_path(path):
    urls = [(r'^$', generateLabConfigHtml),(r'^static/style.css$', getCSS)]
    matchpath = path.lstrip('/')
    for regexp, func in urls:
        match = re.match(regexp, matchpath)
        if match is None:
            continue
        args = match.groups([])
        return func, args
    # we get here if no url matches
    raise NameError

def application(environ, start_response):
    status = "200 OK"
    headers = [('Content-type', 'text/html')]
    try:
        path = environ.get('PATH_INFO',None)
        if path is None:
            raise NameError
        func, args = resolve_path(path)
        body = func(*args)
        status = "200 OK"
    except NameError:
        status = "404 Not Found"
        body = "<h1>Not Found</h1>"
    except Exception:
        status = "500 Internal Server Error"
        body = "<h1>Internal Server Error</h1>"
    finally:
        headers.append(('Content-length', str(len(body))))
        start_response(status,headers)
        #import pdb;pdb.set_trace()
        return [body]
    
    start_response(status, headers)
    return ["<h1>No Progress Yet</h1>", ]

if __name__ == '__main__':
    #read config files
    try:
        confStr = open(configPath,'r').read()
        config = json.loads(confStr)
        #import pdb;pdb.set_trace()
        infoCmdLst = config["InfoCmds"]
        ipLst = config["TrainerIps"]
    except IOError, e:
        print 'Could not open config file %s. Closing App.\n%r' % (configPath,e)
        sys.exit(1)
    except ValueError, e:
        print 'Could not parse config file %s. Closing App.\n%r' % (configPath,e)
    else:
        #setup and run server        
        from wsgiref.simple_server import make_server
        srv = make_server('localhost', 8090, application)
        srv.serve_forever()