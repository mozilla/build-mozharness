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
from Log import SimpleFileLogger, BasicFunctions

import Config
reload(Config)
from Config import SimpleConfig



# MaemoDebSigner {{{1
class MaemoDebSigner(SimpleConfig, BasicFunctions):
    def __init__(self, configFile=None):
        """I wanted to inherit BasicFunctions in SimpleFileLogger but
        that ends up not carrying down to this object since SimpleConfig
        doesn't inherit the logger, just has a self.logObj.
        """
        SimpleConfig.__init__(self, configFile=configFile)
        BasicFunctions.__init__(self)

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
        parser.add_option("--debname", action="store", dest="debname",
                          type="string",
                          help="Specify the name of the deb")
        parser.add_option("--configFile", action="store", dest="configFile",
                          type="string",
                          help="Specify the config file (required)")
        (options, args) = parser.parse_args()

        if not options.configFile:
            self.fatal("You must specify --configFile!")
        else:
            self.setConfig(self.parseConfigFile(options.configFile))

        for option in parser.variables:
             self.setVar(option, getattr(options, option))

    def queryDebName(self, debNameUrl=None):
        debName = self.queryVar('debname')
        if debName:
            return debName
        if debNameUrl:
            self.info('Getting debName from %s' % debNameUrl)
            try:
                ul = urllib2.build_opener()
                fh = ul.open(debNameUrl)
                debName = fh.read().rstrip()
                self.debug('Deb name is %s' % debName)
                return debName
            except HTTPError, e:
                self.fatal("HTTP Error: %s %s" % (e.code, url))
            except URLError, e:
                self.fatal("URL Error: %s %s" % (e.code, url))

    def clobberRepoDir(self):
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        repoDir = self.queryVar("repoDir")
        if not workDir or not baseWorkDir or not repoDir:
            self.fatal("baseWorkDir, workDir, repoDir need to be set!")
        repoPath = os.path.join(baseWorkDir, workDir, repoDir)
        if os.path.exists(repoPath):
            self.rmtree(repoPath)

    def queryLocales(self, platform, platformConfig=None):
        locales = self.queryVar("locales")
        if not locales:
            locales = []
            if not platformConfig:
                platformConfig = self.queryVar("platformConfig")
            pf = platformConfig[platform]
            localesFile = self.queryVar("localesFile")
            if "multiDirUrl" in pf:
                locales.append("multi")
            if "enUsDirUrl" in pf:
                locales.append("en-US")
            if "l10nDirUrl" in pf and localesFile:
                """This assumes all locales in the l10n json file
                are applicable. If not, we'll have to parse the json
                for matching platforms.
                """
                if localesFile.endswith(".json"):
                    localesJson = self.parseConfigFile(localesFile)
                    locales.extend(localesJson.keys())
                else:
                    fh = open(localesFile)
                    additionalLocales = fh.read().split()
                    locales.extend(additionalLocales)
        return locales

    def signRepo(self, baseWorkDir, workDir, repoDir, repoName, platform,
                 section, sboxPath="/scratchbox/moz_scratchbox"):
        sboxWorkDir = '%s/%s/%s' % (workDir, repoDir, repoName)
        absWorkDir = '%s/%s' % (baseWorkDir, sboxWorkDir)

        # TODO errorRegex
        errorRegex = []
        command = "%s -p -d %s apt-ftparchive packages " % (sboxPath, sboxWorkDir)
        command += "dists/%s/%s/binary-armel |" % (platform, section)
        command += "gzip -9c > %s/dists/%s/%s/binary-armel/Packages.gz" % \
                   (absWorkDir, platform, section)
        if self.runCommand(command, errorRegex=errorRegex):
            self.error("Exiting signRepo.")
            return -1

        for subDir in ("dists/%s/%s/binary-armel" % (platform, section),
                       "dists/%s/%s" % (platform, section),
                       "dists/%s" % platform):
            self.rmtree("%s/%s/Release.gpg" % (absWorkDir, subDir))
            # Create Release file outside of the tree, then move in.
            # TODO errorRegex
            errorRegex=[]
            command = "%s -p -d %s/%s " % (sboxPath, sboxWorkDir, subDir)
            command += "apt-ftparchive release . > %s/Release.tmp" % absWorkDir
            if self.runCommand(command, errorRegex=errorRegex):
                self.error("Exiting signRepo.")
                return -2
            self.move("%s/Release.tmp" % absWorkDir,
                      "%s/%s/Release" % (absWorkDir, subDir))

            errorRegex = [{'regex': 'command not found', 'level': 'error'},
                          {'regex': 'secret key not available', 'level': 'error'},
                         ]
            command = "gpg -abs -o Release.gpg Release"
            if self.runCommand(command, errorRegex=errorRegex,
                               cwd='%s/%s' % (absWorkDir, subDir)):
                self.error("Exiting signRepo.")
                return -3
        return 0

    def createInstallFile(self, filePath, replaceDict):
        contents = """[install]
repo_deb_3 = deb %(repoUrl)s %(platform)s %(section)s
catalogues = %(shortCatalogName)s
package = %(packageName)s

[fennec]
name =     Mozilla %(longCatalogName)s %(locale)s Catalog
uri = %(repoUrl)s
dist = %(platform)s
components = %(section)s
""" % replaceDict
        self.info("Writing install file to %s" % filePath)
        fh = open(filePath, 'w')
        print >> fh, contents
        fh.close()
        

    def createRepos(self):
        """
        This method is getting a little long... I could split a lot of it
        out if I weren't trying to optimize for the fewest queryVar()s
        for some strange reason.
        """
        baseRepoUrl = self.queryVar("baseRepoUrl")
        baseWorkDir = self.queryVar("baseWorkDir")
        hgMobileRepo = self.queryVar("hgMobileRepo")
        hgConfigRepo = self.queryVar("hgConfigRepo")
        packageName = self.queryVar("packageName")
        platformConfig = self.queryVar("platformConfig")
        platforms = self.queryVar("platforms")
        repoDir = self.queryVar("repoDir")
        sboxPath = self.queryVar("sboxPath")
        section = self.queryVar("section")
        workDir = self.queryVar("workDir")

        if not platforms:
            platforms = platformConfig.keys()

        self.clobberRepoDir()

        hgErrorRegex=[{'regex': '^abort:', 'level': 'error'},
                     ]
        if hgMobileRepo is not None:
            if not os.path.exists('mobile'):
                self.runCommand("hg clone %s mobile" % hgMobileRepo,
                                errorRegex=hgErrorRegex)
            self.runCommand("hg --cwd mobile pull", errorRegex=hgErrorRegex)
            self.runCommand("hg --cwd mobile update -C", errorRegex=hgErrorRegex)
        if hgConfigRepo is not None:
            if not os.path.exists('configs'):
                self.runCommand("hg clone %s configs" % hgConfigRepo,
                                errorRegex=hgErrorRegex)
            self.runCommand("hg --cwd configs pull", errorRegex=hgErrorRegex)
            self.runCommand("hg --cwd configs update -C", errorRegex=hgErrorRegex)

        for platform in platforms:
            """This assumes the same deb name for each locale in a platform.
            """
            self.info("###%s###" % platform)
            pf = platformConfig[platform]
            debName = self.queryDebName(debNameUrl=pf['debNameUrl'])
            locales = self.queryLocales(platform, platformConfig=platformConfig)
            for locale in locales:
                replaceDict = {'locale': locale,
                               'longCatalogName': pf['longCatalogName'],
                               'packageName': packageName,
                               'platform': platform,
                               'section': section,
                               'shortCatalogName': pf['shortCatalogName'],
                              }
                installFile = pf['installFile'] % replaceDict
                repoName = self.queryVar('repoName') % replaceDict
                repoUrl = '%s/%s' % (baseRepoUrl, repoName)
                replaceDict['repoUrl'] = repoUrl
                debUrl = ''
                if locale == 'multi':
                    debUrl = pf['multiDirUrl']
                elif locale == 'en-US':
                    debUrl = pf['enUsDirUrl']
                else:
                    debUrl = '%s/%s' % (pf['l10nDirUrl'], locale)
                debUrl += '/%s' % debName
                self.debug(debUrl)
                if not self.downloadFile(debUrl, debName):
                    self.warn("Skipping %s ..." % locale)
                    continue
                binaryDir = '%s/%s/%s/dists/%s/%s/binary-armel' % \
                            (workDir, repoDir, repoName, platform, section)
                absBinaryDir = '%s/%s' % (baseWorkDir, binaryDir)
                self.mkdir_p(absBinaryDir)
                self.move(debName, absBinaryDir)

                # Not sure I like this syntax
                if self.signRepo(baseWorkDir, workDir, repoDir, repoName,
                                 platform, section, sboxPath=sboxPath) != 0:
                    self.error("Skipping %s %s" % (platform, locale))
                    continue

                self.createInstallFile(os.path.join(baseWorkDir, workDir,
                                                    repoDir, repoName,
                                                    installFile),
                                       replaceDict)
                self.uploadRepo(os.path.join(baseWorkDir, workDir, repoDir),
                                repoName, platform, installFile)

    def uploadRepo(self, localRepoDir, repoName, platform, installFile):
        remoteRepoPath = self.queryVar("remoteRepoPath")
        remoteUser = self.queryVar("remoteUser")
        remoteSshKey = self.queryVar("remoteSshKey")
        remoteHost = self.queryVar("remoteHost")

        # TODO errorRegex
        errorRegex=[{'regex': 'Name or service not known', 'level': 'error'},
                    {'regex': 'Could not resolve hostname', 'level': 'error'},
                    {'regex': 'POSSIBLE BREAK-IN ATTEMPT', 'level': 'warning'},
                    {'regex': 'Network error:', 'level': 'error'},
                    {'regex': 'Access denied', 'level': 'error'},
                    {'regex': 'Authentication refused', 'level': 'error'},
                    {'regex': 'Out of memory', 'level': 'error'},
                    {'regex': 'Connection reset by peer', 'level': 'warning'},
                    {'regex': 'Host key verification failed', 'level': 'error'},
                    {'regex': 'command not found', 'level': 'error'},
                    {'regex': 'WARNING:', 'level': 'warning'},
                    {'regex': 'rsync error:', 'level': 'error'},
                    {'regex': 'Broken pipe:', 'level': 'error'},
                    {'regex': 'connection unexpectedly closed:', 'level': 'error'},
                   ]
        command = "ssh -i %s %s@%s mkdir -p %s/%s/dists/%s" % \
                  (remoteSshKey, remoteUser, remoteHost, remoteRepoPath,
                   repoName, platform)
        self.runCommand(command, errorRegex=errorRegex)

        command = 'rsync --rsh="ssh -i %s" -azv --delete %s %s@%s:%s/%s/dists/%s' % \
                  (remoteSshKey,
                   os.path.join(localRepoDir, repoName, 'dists', platform, '.'),
                   remoteUser, remoteHost, remoteRepoPath, repoName, platform)
        self.runCommand(command, errorRegex=errorRegex)

        command = 'scp -i %s %s %s@%s:%s/%s/' % \
                  (remoteSshKey,
                   os.path.join(localRepoDir, repoName, installFile),
                   remoteUser, remoteHost, remoteRepoPath, repoName)
        self.runCommand(command, errorRegex=errorRegex)



# __main__ {{{1
if __name__ == '__main__':
    debSigner = MaemoDebSigner()
    debSigner.createRepos()
