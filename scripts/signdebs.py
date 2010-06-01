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



# MaemoDebSigner {{{1
class MaemoDebSigner(SimpleConfig):
    def __init__(self, configFile=None, localesFile=None, locales=None):
        SimpleConfig.__init__(self, configFile=configFile)

    def parseArgs(self):
        """I want to change this to send the list of options to
        Config.parseArgs() but don't know a way to intuitively do that.
        Each add_option seems to take *args and **kwargs, so it would be

            complexOptionList = [
             [["-f", "--file"], {"dest": "filename", "help": "blah"}],
             [*args, **kwargs],
             [*args, **kwargs],
             ...
            ]
            SimpleConfig.parseArgs(self, options=complexOptionList)

        Not very pretty, but having the options logic in every inheriting
        script isn't that great either.
        """
        parser = SimpleConfig.parseArgs(self)
        parser.add_option("--locale", action="append", dest="locales",
                          type="string",
                          help="Specify the locale(s) to repack")
        parser.add_option("--platform", action="append", dest="platforms",
                          type="string",
                          help="Specify the platform(s) to repack")
        (options, args) = parser.parse_args()
        for option in parser.variables:
             self.setVar(option, getattr(options, option))

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

    def clobberRepoDir(self):
        repoDir = self.queryVar("repoDir")
        if not repoDir:
            self.fatal("clobberRepoDir: repoDir not set!")
        if os.path.exists(repoDir):
            self.rmtree(repoDir)

    def createRepos(self):
        self.clobberRepoDir()
        repoDir = self.queryVar("repoDir")
        self.mkdir_p(repoDir)



# __main__ {{{1
if __name__ == '__main__':
    debSigner = MaemoDebSigner(configFile='%s/configs/deb_repos/trunk_nightly.json' % sys.path[0])

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
