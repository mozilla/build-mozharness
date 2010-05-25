#!/usr/bin/env python
"""signdebs.py

Usage:
    signdebs.py [args]
"""

import os
import shutil
import subprocess
import sys
import urllib2
from urllib2 import Request, urlopen, URLError, HTTPError

# load modules from parent dir
sys.path[0] = os.path.dirname(sys.path[0])

import Log
reload(Log)
from Log import SimpleFileLogger

import Config
reload(Config)
from Config import SimpleConfig



# MaemoDebSigner {{{1
class MaemoDebSigner(SimpleConfig, SimpleFileLogger):
    def __init__(self, logLevel='info', logName='debsign.log',
                 configFile=None, localesFile=None, locales=None):
        SimpleFileLogger.__init__(self, logName=logName,
                                  defaultLogLevel=logLevel)
        SimpleConfig.__init__(self, configFile=configFile)

    def getDebName(self):
        if self.debName:
            return self.debName
        debName = self.queryVar('debName')
        if debName:
            self.debug('Setting deb name from config: %s' % debName)
            self.debName = debName
            return debName
        debNameUrl = None
        if self.debNameUrl:
            debNameUrl = self.debNameUrl
        else:
            debNameUrl = self.queryVar('debNameUrl')
        if debNameUrl:
            self.info('Getting debName from %s' % debNameUrl)
            ul = urllib2.build_opener()
            fh = ul.open(debNameUrl)
            self.debName = fh.read()[:-1]
            self.debug('Deb name is %s' % self.debName)
            return self.debName

def mkdir_p(path):
    print "mkdir: %s" % path
    if not os.path.exists(path):
        print "yes"
        os.makedirs(path)
    else:
        print "already exists"


def getPlatformLocales(platformConfig):
    platformLocales = []
    if 'multiDirUrl' in platformConfig:
        platformLocales.append('multi')
    if 'enUsDirUrl' in platformConfig:
        platformLocales.append('en-US')
    if 'l10nDirUrl' in platformConfig:
        platformLocales.extend(locales)
    return platformLocales

def parseArgs():
    # TODO parse cmdln args
    configFile='%s/configs/deb_repos/trunk_nightly.json' % sys.path[0]
    platforms=None
    locales=None
    fh = open(configFile)
    configJson = json.load(fh)
    config = json.JSONDecoder().decode(configJson)
    if platforms is None:
        platforms = config['platforms'].keys()

    return (config, platforms, locales)

# http://www.techniqal.com/blog/2008/07/31/python-file-read-write-with-urllib2/
def downloadFile(url, fileName):
    req = Request(url)

    # TODO remove these
    os.system("touch %s" % fileName)
    return fileName

    try:
        print "Downloading %s" % url
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

def signRepo(config, repoName, platform):
    # TODO sign
    pass



# __main__ {{{1
if __name__ == '__main__':
    debSigner = MaemoDebSigner(logLevel='debug')
    # repoDir is assumed to be relative from /scratchbox/users/cltbld/home/cltbld
#    if os.path.exists(config['repoDir']):
#        shutil.rmtree(config['repoDir'])
#    mkdir_p(config['repoDir'])
#
#    for platform in platforms:
#        print "###%s###" % platform
#        platformConfig = config['platforms'][platform]
#        platformLocales = getPlatformLocales(platformConfig)
#
#        signObj = MaemoDebSigner(configJson=platformConfig)
#        print signObj.debNameUrl
#        debName = signObj.getDebName()
#        print debName
#
#        # Assuming the deb name is consistent across all locales for a platform
#
#        for locale in platformLocales:
#            repoName = config['repoName'].replace('LOCALE', locale)
#            installFile = platformConfig['installFile'].replace('LOCALE', locale)
#            url = ''
#            if locale == 'multi':
#                url = platformConfig['multiDirUrl']
#            elif locale == 'en-US':
#                url = platformConfig['enUsDirUrl']
#            else:
#                url = '%s/%s' % (platformConfig['l10nDirUrl'], locale)
#            url += '/%s' % debName
#            if not downloadFile(url, debName):
#                print "Skipping %s ..." % locale
#                continue
#
#            binaryDir = '%s/%s/dists/%s/%s/binary-armel' % \
#                        (config['repoDir'], repoName, platform,
#                         config['section'])
#            absBinaryDir = '%s/%s' % (config['baseWorkDir'], binaryDir)
#            mkdir_p(absBinaryDir)
#            shutil.move(debName, absBinaryDir)
#            signRepo(config, repoName, platform)
#
#            # TODO create install file
#            # TODO upload
