#!/usr/bin/env python
"""signdebs.py

Usage:
    signdebs.py [args]

TODO: make createRepos and signRepo(s) more standalone for discrete actions
"""

import os
import shutil
import subprocess
import sys
import urllib2
from urllib2 import URLError, HTTPError

# load modules from parent dir
sys.path[0] = os.path.dirname(sys.path[0])

import log
reload(log)
from log import SimpleFileLogger, BasicFunctions, SSHErrorRegexList, HgErrorRegexList

import config
reload(config)
from config import SimpleConfig



# MaemoDebSigner {{{1
class MaemoDebSigner(SimpleConfig):
    def __init__(self, requireConfigFile=True):
        """I wanted to inherit BasicFunctions in SimpleFileLogger but
        that ends up not carrying down to this object since SimpleConfig
        doesn't inherit the logger, just has a self.logObj.
        """
        configOptions = [[
         ["--locale",],
         {"action": "append_split",
          "dest": "locales",
          "type": "string",
          "help": "Specify the locale(s) to repack"
         }
        ],[
         ["--platform",],
         {"action": "append_split",
          "dest": "platforms",
          "type": "string",
          "help": "Specify the platform(s) to repack"
         }
        ],[
         ["--debName",],
         {"action": "store",
          "dest": "debName",
          "type": "string",
          "help": "Specify the name of the deb"
         }
        ]]
        SimpleConfig.__init__(self, configOptions=configOptions,
                              allActions=['clobber', 'createRepos',
                                          'upload'],
                              requireConfigFile=requireConfigFile)
        self.failures = []

    def run(self):
        self.clobberRepoDir()
        self.createRepos()
        self.uploadRepos()
        if self.failures:
            self.error("%s failures: %s" % (self.__class__.__name__,
                                            self.failures))

    def _queryDebName(self, debNameUrl=None):
        debName = self.queryVar('debName')
        if debName:
            return debName
        if debNameUrl:
            self.info('Getting debName from %s' % debNameUrl)
            # TODO belongs in downloadFile or equivalent?
            try:
                ul = urllib2.build_opener()
                fh = ul.open(debNameUrl)
                debName = fh.read().rstrip()
                self.debug('Deb name is %s' % debName)
                return debName
            except HTTPError, e:
                self.error("HTTP Error: %s %s" % (e.code, debNameUrl))
            except URLError, e:
                self.error("URL Error: %s %s" % (e.code, debNameUrl))

    def clobberRepoDir(self):
        if not self.queryAction('clobber'):
            self.info("Skipping clobber step.")
            return
        self.info("Clobbering repo dir.")
        base_work_dir = self.queryVar("base_work_dir")
        work_dir = self.queryVar("work_dir")
        repo_dir = self.queryVar("repo_dir")
        if not work_dir or not base_work_dir or not repo_dir:
            self.fatal("base_work_dir, work_dir, repo_dir need to be set!")
        repoPath = os.path.join(base_work_dir, work_dir, repo_dir)
        if os.path.exists(repoPath):
            self.rmtree(repoPath)
        else:
            self.debug("%s doesn't exist." % repoPath)

    def _queryLocales(self, platform, platformConfig=None):
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

    def _signRepo(self, repoName, platform):
        base_work_dir = self.queryVar("base_work_dir")
        repo_dir = self.queryVar("repo_dir")
        sboxPath = self.queryVar("sboxPath")
        section = self.queryVar("section")
        work_dir = self.queryVar("work_dir")
        sbox_work_dir = '%s/%s/%s' % (work_dir, repo_dir, repoName)
        abs_work_dir = '%s/%s' % (base_work_dir, sbox_work_dir)

        # TODO errorRegex
        errorRegexList = []
        command = "%s -p -d %s apt-ftparchive packages " % (sboxPath, sbox_work_dir)
        command += "dists/%s/%s/binary-armel |" % (platform, section)
        command += "gzip -9c > %s/dists/%s/%s/binary-armel/Packages.gz" % \
                   (abs_work_dir, platform, section)
        status = self.runCommand(command, errorRegexList=errorRegexList)
        if status:
            self.error("Exiting signRepo.")
            return status

        for sub_dir in ("dists/%s/%s/binary-armel" % (platform, section),
                       "dists/%s/%s" % (platform, section),
                       "dists/%s" % platform):
            self.rmtree("%s/%s/Release.gpg" % (abs_work_dir, sub_dir))
            # Create Release file outside of the tree, then move in.
            # TODO errorRegexList
            errorRegexList=[]
            command = "%s -p -d %s/%s " % (sboxPath, sbox_work_dir, sub_dir)
            command += "apt-ftparchive release . > %s/Release.tmp" % abs_work_dir
            if self.runCommand(command, errorRegexList=errorRegexList):
                self.error("Exiting signRepo.")
                return -2
            self.move("%s/Release.tmp" % abs_work_dir,
                      "%s/%s/Release" % (abs_work_dir, sub_dir))

            errorRegexList = [{'regex': 'command not found', 'level': 'error'},
                          {'regex': 'secret key not available', 'level': 'error'},
                         ]
            command = "gpg -abs -o Release.gpg Release"
            if self.runCommand(command, errorRegexList=errorRegexList,
                               cwd='%s/%s' % (abs_work_dir, sub_dir)):
                self.error("Exiting signRepo.")
                return -3
        return 0

    def _createInstallFile(self, filePath, locale, platform):
        baseRepoUrl = self.queryVar("baseRepoUrl")
        packageName = self.queryVar("packageName")
        platformConfig = self.queryVar("platformConfig")
        section = self.queryVar("section")
        pf = platformConfig[platform]
        replaceDict = {'locale': locale,
                       'longCatalogName': pf['longCatalogName'],
                       'packageName': packageName,
                       'platform': platform,
                       'section': section,
                       'shortCatalogName': pf['shortCatalogName'],
                      }
        repoName = self.queryVar('repoName') % replaceDict
        replaceDict['repoUrl'] = '%s/%s' % (baseRepoUrl, repoName)
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
        if not self.queryAction('createRepos'):
            self.info("Skipping create repo step.")
            return
        self.info("Creating repos.")
        base_work_dir = self.queryVar("base_work_dir")
        hgMobileRepo = self.queryVar("hgMobileRepo")
        hgConfigRepo = self.queryVar("hgConfigRepo")
        platformConfig = self.queryVar("platformConfig")
        platforms = self.queryVar("platforms", default=platformConfig.keys())
        repo_dir = self.queryVar("repo_dir")
        sboxPath = self.queryVar("sboxPath")
        section = self.queryVar("section")
        work_dir = self.queryVar("work_dir")

        if hgMobileRepo is not None:
            if not os.path.exists('mobile'):
                self.runCommand("hg clone %s mobile" % hgMobileRepo,
                                errorRegexList=HgErrorRegexList)
            self.runCommand("hg --cwd mobile pull", errorRegexList=HgErrorRegexList)
            self.runCommand("hg --cwd mobile update -C", errorRegexList=HgErrorRegexList)
        if hgConfigRepo is not None:
            if not os.path.exists('configs'):
                self.runCommand("hg clone %s configs" % hgConfigRepo,
                                errorRegexList=HgErrorRegexList)
            self.runCommand("hg --cwd configs pull", errorRegexList=HgErrorRegexList)
            self.runCommand("hg --cwd configs update -C", errorRegexList=HgErrorRegexList)

        for platform in platforms:
            """This assumes the same deb name for each locale in a platform.
            """
            self.info("%s" % platform)
            pf = platformConfig[platform]
            debName = self._queryDebName(debNameUrl=pf['debNameUrl'])
            if not debName:
                continue
            locales = self._queryLocales(platform, platformConfig=platformConfig)
            for locale in locales:
                replaceDict = {'locale': locale}
                installFile = pf['installFile'] % replaceDict
                repoName = self.queryVar('repoName') % replaceDict
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
                binary_dir = '%s/%s/%s/dists/%s/%s/binary-armel' % \
                             (work_dir, repo_dir, repoName, platform, section)
                abs_binary_dir = '%s/%s' % (base_work_dir, binary_dir)
                self.mkdir_p(abs_binary_dir)
                self.move(debName, abs_binary_dir)

                if self._signRepo(repoName, platform) != 0:
                    self.error("Skipping %s %s" % (platform, locale))
                    self.failures.append('%s_%s' % (platform, locale))
                    continue

                self._createInstallFile(os.path.join(base_work_dir, work_dir,
                                                    repo_dir, repoName,
                                                    installFile),
                                       locale, platform)

    def uploadRepos(self):
        if not self.queryAction('upload'):
            self.info("Skipping upload step.")
            return
        self.info("Uploading repos.")
        base_work_dir = self.queryVar("base_work_dir")
        platformConfig = self.queryVar("platformConfig")
        platforms = self.queryVar("platforms", default=platformConfig.keys())
        repo_dir = self.queryVar("repo_dir")
        work_dir = self.queryVar("work_dir")
        for platform in platforms:
            """This assumes the same deb name for each locale in a platform.
            """
            self.info("%s" % platform)
            pf = platformConfig[platform]
            locales = self._queryLocales(platform, platformConfig=platformConfig)
            for locale in locales:
                if '%s_%s' % (platform, locale) not in self.failures:
                    replaceDict = {'locale': locale}
                    installFile = pf['installFile'] % replaceDict
                    repoName = self.queryVar('repoName') % replaceDict
                    self._uploadRepo(os.path.join(base_work_dir, work_dir, repo_dir),
                                     repoName, platform, installFile)

    def _uploadRepo(self, local_repo_dir, repoName, platform, installFile):
        remoteRepoPath = self.queryVar("remoteRepoPath")
        remoteUser = self.queryVar("remoteUser")
        remoteSshKey = self.queryVar("remoteSshKey")
        remoteHost = self.queryVar("remoteHost")
        repoPath = os.path.join(local_repo_dir, repoName, 'dists', platform)
        installFilePath = os.path.join(local_repo_dir, repoName, installFile)

        if not os.path.isdir(repoPath):
            self.error("uploadRepo: %s isn't a valid repo!" % repoPath)
            return -1
        if not os.path.exists(installFilePath):
            self.error("uploadRepo: %s doesn't exist!" % installFilePath)

        command = "ssh -i %s %s@%s mkdir -p %s/%s/dists/%s" % \
                  (remoteSshKey, remoteUser, remoteHost, remoteRepoPath,
                   repoName, platform)
        self.runCommand(command, errorRegexList=SSHErrorRegexList)

        command = 'rsync --rsh="ssh -i %s" -azv --delete %s %s@%s:%s/%s/dists/%s' % \
                  (remoteSshKey, os.path.join(repoPath, '.'),
                   remoteUser, remoteHost, remoteRepoPath, repoName, platform)
        self.runCommand(command, errorRegexList=SSHErrorRegexList)

        command = 'scp -i %s %s %s@%s:%s/%s/' % \
                  (remoteSshKey, installFilePath,
                   remoteUser, remoteHost, remoteRepoPath, repoName)
        self.runCommand(command, errorRegexList=SSHErrorRegexList)



# __main__ {{{1
if __name__ == '__main__':
    debSigner = MaemoDebSigner()
    debSigner.run()
