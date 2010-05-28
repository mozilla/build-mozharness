#!/usr/bin/env python
"""Shared functions.
Not sure if this is the best method of doing this, but works for now.
"""
import os
import shutil
import urllib2

def mkdir_p(logObj, path):
    logObj.info("mkdir: %s" % path)
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        logObj.info("Already exists.")

def rmtree(logObj, path, errorLevel='error'):
    logObj.info("rmtree: %s" % path)
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        if os.path.exists(path):
            logObj.log(errorLevel, 'Unable to remove %s!' % path)
    else:
        logObj.debug("%s doesn't exist.")

# http://www.techniqal.com/blog/2008/07/31/python-file-read-write-with-urllib2/
def downloadFile(logObj, url, fileName=None, testOnly=False):
    """Python wget.
    TODO: option to mkdir_p dirname(fileName) if it doesn't exist.
    """
    if not fileName:
        fileName = os.basename(url)
    if testOnly:
        os.system("touch %s" % fileName)
        return fileName

    req = urllib2.Request(url)
    try:
        logObj.info("Downloading %s" % url)
        f = urlopen(req)
        localFile = open(fileName, 'w')
        localFile.write(f.read())
        localFile.close()
    except HTTPError, e:
        print "HTTP Error:", e.code, url
        return
    except URLError, e:
        print "URL Error:", e.code, url
        return
    return fileName



if __name__ == '__main__':
    pass
