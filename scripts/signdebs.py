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
from urllib2 import URLError, HTTPError

# load modules from parent dir
sys.path[0] = os.path.dirname(sys.path[0])

import Log
reload(Log)
from Log import SimpleFileLogger

import Config
reload(Config)
from Config import SimpleConfig

import Functions
reload(Functions)



# MaemoDebSigner {{{1
class MaemoDebSigner(SimpleConfig):
    def __init__(self, configFile=None, localesFile=None, locales=None):
        SimpleConfig.__init__(self, configFile=configFile)
        self.debug(self.dumpConfig())

    def parseArgs(self):
        parser = SimpleConfig.parseArgs(self)
        parser.add_option("-f", "--file", dest="filename",
                          help="write report to FILE", metavar="FILE")
        (options, args) = parser.parse_args()
        print "Options:", options

    def getDebName(self, debNameUrl=None):
        if debNameUrl:
            self.info('Getting debName from %s' % debNameUrl)
            try:
                ul = urllib2.build_opener()
                fh = ul.open(debNameUrl)
                debName = fh.read()[:-1] # chomp
                self.debug('Deb name is %s' % debName)
                return debName
            except HTTPError, e:
                self.fatal("HTTP Error: %s %s" % (e.code, url))
            except URLError, e:
                self.fatal("URL Error: %s %s" % (e.code, url))

    def mkdir_p(self, path):
        Functions.mkdir_p(self, path)

    def rmtree(self, path):
        Functions.rmtree(self, path, errorLevel='fatal')

    def downloadFile(self, url, fileName=None):
        # TODO remove testOnly
        return Functions.downloadFile(self, url, fileName=fileName, testOnly=True)



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

def signRepo(config, repoName, platform):
    # TODO sign
    pass



# __main__ {{{1
if __name__ == '__main__':
    debSigner = MaemoDebSigner(configFile='%s/configs/deb_repos/trunk_nightly.json' % sys.path[0])
    # repoDir is assumed to be relative from /scratchbox/users/cltbld/home/cltbld
    config = debSigner.queryConfig()
    if os.path.exists(config['repoDir']):
        debSigner.rmtree(config['repoDir'])
    debSigner.mkdir_p(config['repoDir'])

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
