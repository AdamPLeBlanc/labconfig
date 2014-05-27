#!/usr/bin/env python
import sys
import json
import re
import os
from string import Template
from collections import OrderedDict
from datetime import datetime

mainTemplate = Template('''
<html>
<head>
    <link rel="stylesheet" type="text/css" href="static/style.css">
    <title>Lab Config</title>
</head>
<body>
    <div class="accent">
        <ul class="menu">
            <li class="menu"><a class="menu" href="labconfig">Lab Config</a></li>
            <li class="menu"><a class="menu" href="backlogsummary">Backlog Summary</a></li>
        </ul>
    </div>
        $Body
    <div class="accent">
        last updated $Date
    </div>
</body>
</html>''')

configPath = "labConfig.json"
bliInfoPath = "bliInfo.json"
infoCmdLst = None
ipLst = None
bliInfoList = None

def wrapElement(tag,content,**attrs):
    #import pdb; pdb.set_trace()
    retVal = ''
    attrStr = ''
    tmplt = "<%s%s>%s</%s>"
    if attrs:
        attrStr = ' %s' % ' '.join(['%s=%s' %(key,val) for key, val in attrs.items()])    
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
    retVal = os.popen(cmd).read() #will return 'infoTitle:infoDesription\r\ninfoTitle:infoDescription\r\n..' string'
    return [map(str.strip,line.split(':')) for line in retVal.splitlines() if line]

def getSubSystemRowData(ssName):
    cmdRetVals = OrderedDict()
    cmd = infoCmdLst.get(ssName,'')
    ips = ipLst.values()
    cntr = -1
    for sysInfo in ips: # returns dict of subsystem ip addresses for each trainer
        cntr += 1
        for i in execCmd(cmd,sysInfo.get(ssName,'')):
            tmpLst = cmdRetVals.get(i[0],['']*len(ips))
            tmpLst[cntr] = i[1]
            cmdRetVals[i[0]] = tmpLst
    rowItems = []
    for name, descList in cmdRetVals.items():
        tmpList = []
        tmpList.append(wrapElement('td',name,**{'class':'"dataHdr"'}))
        tmpList += [wrapElement('td',i,**{'class':'"data"'}) for i in descList]
        rowItems.append(wrapRow('\n'.join(tmpList)))

    return '\n'.join(rowItems)

def getBliRowData(bliInfo):
    tds = [wrapElement('td',item,**{'class':'"data"'}) for item in bliInfo]
    #import pdb;pdb.set_trace()
    return wrapRow('\n'.join(tds))

#called when user looks up 'website'/local/style.css
def getCSS():
    return open('templates/style.css','rb').read()

#called when user looks up 'website'/ or 'website/labconfig'
def generateLabConfigHtml():
    tblContent = []
    trainers = ipLst.keys()
    #add column headers
    tblContent.append(wrapRow('\n'.join([wrapElement('td','',**{'class':'"labCfgColHdr"'})]+
        [wrapElement('th',val,**{'class':'"labCfgColHdr"'}) for val in trainers])))
    #for each trainer get lab config info for each subsystem
    for ss, cmdInfo in infoCmdLst.items():
        tblContent.append(wrapRow(wrapElement('td',ss,**{'class':'"lngRow"','colspan':'100%'})))
        tblContent.append(getSubSystemRowData(ss))
    #import pdb;pdb.set_trace()
    body = mainTemplate.substitute({"Body":wrapElement('div',wrapElement('table','\n'.join(tblContent))), \
        "Date":datetime.today().strftime('%b-%d-%Y @ %H:%M:%S')})

    return body

#called when user looks up 'website/backlogsummary'
def generateBacklogSummaryHtml():
    tblContent = []
    #add column headers
    colHdrs = ['ID','Title','Team','Status','Activity Id','Build for Latest Change']
    tblContent.append(wrapRow('\n'.join([wrapElement('th',val,**{'class':'"bliInfoColHdr"'}) for val in colHdrs])))
    #for each bli get information and add it to table
    for bliInfo in bliInfoList:
        tmp = getBliRowData(bliInfo)
        tblContent.append(tmp)
    #import pdb;pdb.set_trace()
    divCnts = wrapElement('div',wrapElement('table','\n'.join(tblContent)))
    dateCnts = datetime.today().strftime('%b-%d-%Y @ %H:%M:%S')
    body = mainTemplate.substitute({"Body":divCnts,"Date":dateCnts})

    return body

def resolvePath(path):    
    urls = [(r'^$', generateLabConfigHtml),(r'^labconfig',generateLabConfigHtml), \
            (r'^static/style.css$', getCSS),(r'^backlogsummary',generateBacklogSummaryHtml)]
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
        #import pdb;pdb.set_trace()
        func, args = resolvePath(path)
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
        fPath = configPath
        config = json.loads(open(fPath,'r').read())
        infoCmdLst = config["InfoCmds"]
        ipLst = config["TrainerIps"]
        fPath = bliInfoPath
        bliInfoList = json.loads(open(fPath,'r').read())
    except IOError, e:
        print 'Could not open config file %s. Closing App.\n%r' % (fPath,e)
    except ValueError, e:
        print 'Could not parse config file %s. Closing App.\n%r' % (fPath,e)
    except KeyError, e:
        print 'Could not extract all needed config values\n%r' % e
    else:
        #setup and run server        
        from wsgiref.simple_server import make_server
        srv = make_server('localhost', 8090, application)
        srv.serve_forever()