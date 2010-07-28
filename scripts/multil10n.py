#!/usr/bin/env python
"""multil10n.py

Our initial [successful] attempt at a multi-locale repack happened inside
of MaemoBuildFactory.  However, this was highly buildbot-intensive,
requiring runtime step truncation/creation with large amounts of build
properties that disallowed the use of "Force Build" for any multi-locale
nightly.

To improve things, we're moving the logic slave-side where a dedicated
slave can use its cycles determining which locales to repack.
"""

import os
import sys

# load modules from parent dir
sys.path[0] = os.path.dirname(sys.path[0])

import Log
reload(Log)
from Log import SimpleFileLogger, BasicFunctions, SshErrorRegex, HgErrorRegex

import Config
reload(Config)
from Config import SimpleConfig



# MultiLocaleRepack {{{1
class MultiLocaleRepack(SimpleConfig):
    configOptions = [[
     ["--locale",],
     {"action": "append_split",
      "dest": "locales",
      "type": "string",
      "help": "Specify the locale(s) to repack"
     }
    ],[
     ["--repackType",],
     {"action": "store",
      "dest": "repackType",
      "type": "choice",
      "default": "installer",
      "choices": ["installer", "deb"],
      "help": "Choose which type of repack"
     }
    ],[
     ["--mergeLocales",],
     {"action": "store_true",
      "dest": "mergeLocales",
      "default": False,
      "help": "Use default [en-US] if there are missing strings"
     }
    ],[
     ["--noMergeLocales",],
     {"action": "store_false",
      "dest": "mergeLocales",
      "help": "Do not allow missing strings"
     }
    ],[
     ["--enUsBinaryUrl",],
     {"action": "store",
      "dest": "enUsBinaryUrl",
      "type": "string",
      "help": "Specify the en-US binary url"
     }
    ],[
     ["--mozillaRepo",],
     {"action": "store",
      "dest": "hgMozillaRepo",
      "type": "string",
      "help": "Specify the Mozilla repo"
     }
    ],[
     ["--mozillaTag",],
     {"action": "store",
      "dest": "hgMozillaTag",
      "type": "string",
      "help": "Specify the Mozilla tag"
     }
    ],[
     ["--l10nBase",],
     {"action": "store",
      "dest": "hgL10nBase",
      "type": "string",
      "help": "Specify the L10n repo base directory"
     }
    ],[
     ["--l10nTag",],
     {"action": "store",
      "dest": "hgL10nTag",
      "type": "string",
      "help": "Specify the L10n tag"
     }
    ],[
     ["--compareLocalesRepo",],
     {"action": "store",
      "dest": "hgCompareLocalesRepo",
      "type": "string",
      "help": "Specify the compare-locales repo"
     }
    ],[
     ["--compareLocalesTag",],
     {"action": "store",
      "dest": "hgCompareLocalesTag",
      "type": "string",
      "help": "Specify the compare-locales tag"
     }
    ]]

    def __init__(self, requireConfigFile=True):
        """I wanted to inherit BasicFunctions in SimpleFileLogger but
        that ends up not carrying down to this object since SimpleConfig
        doesn't inherit the logger, just has a self.logObj.
        """
        SimpleConfig.__init__(self, configOptions=self.configOptions,
                              allActions=['clobber', 'pull', 'compareLocales',
                                          'repack', 'upload'],
                              requireConfigFile=requireConfigFile)
        self.failures = []
        self.locales = None

    def run(self):
        self.clobber()
        self.pull()
        self.compareLocales()
        self.repack()
        self.upload()
        if self.failures:
            self.error("%s failures: %s" % (self.__class__.__name__,
                                            self.failures))

    def clobber(self):
        if not self.queryAction('clobber'):
            self.info("Skipping clobber step.")
            return
        self.info("Clobbering.")
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        path = os.path.join(baseWorkDir, workDir)
        if os.path.exists(path):
            self.rmtree(path, errorLevel='fatal')

    def queryLocales(self):
        if self.locales:
            return self.locales
        locales = self.queryVar("locales")
        ignoreLocales = self.queryVar("ignoreLocales")
        if not locales:
            locales = []
            workDir = self.queryVar("workDir")
            localesFile = os.path.join(workDir, self.queryVar("localesFile"))
            if localesFile.endswith(".json"):
                localesJson = self.parseConfigFile(localesFile)
                locales = localesJson.keys()
            else:
                fh = open(localesFile)
                locales = fh.read().split()
                fh.close()
            self.debug("Found the locales %s in %s." % (locales, localesFile))
        if ignoreLocales:
            for locale in ignoreLocales:
                if locale in locales:
                    self.debug("Ignoring locale %s." % locale)
                    locales.remove(locale)
        if locales:
            self.locales = locales
            return self.locales

    def _hgPull(self, repo, parentDir, tag="default", dirName=None,
                haltOnFailure=True):
        if not dirName:
            dirName = os.path.basename(repo)
        if not os.path.exists(os.path.join(parentDir, dirName)):
            command = "hg clone %s %s" % (repo, dirName)
        else:
            command = "hg --cwd %s pull" % (dirName)
        self.runCommand(command, cwd=parentDir, haltOnFailure=haltOnFailure,
                        errorRegex=HgErrorRegex)
        command = "hg --cwd %s update -C -r %s" % (dirName, tag)
        self.runCommand(command, cwd=parentDir, haltOnFailure=haltOnFailure,
                        errorRegex=HgErrorRegex)

    def pull(self, repos=None):
        if not self.queryAction('pull'):
            self.info("Skipping pull step.")
            return
        self.info("Pulling.")
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        hgL10nBase = self.queryVar("hgL10nBase")
        hgL10nTag = self.queryVar("hgL10nTag")
        if not repos:
            hgMozillaRepo = self.queryVar("hgMozillaRepo")
            hgMozillaTag = self.queryVar("hgMozillaTag")
            hgCompareLocalesRepo = self.queryVar("hgCompareLocalesRepo")
            hgCompareLocalesTag = self.queryVar("hgCompareLocalesTag")
            repos = [{
                'repo': hgMozillaRepo,
                'tag': hgMozillaTag,
                'dirName': 'mozilla',
            },{
                'repo': hgCompareLocalesRepo,
                'tag': hgCompareLocalesTag,
                'dirName': 'compare-locales',
            }]

        absL10nDir = os.path.join(absWorkDir, "l10n")
        self.mkdir_p(absL10nDir)

        # Chicken/egg: need to pull repos to determine locales.
        # Solve by pulling non-locale repos first.
        for repoDict in repos:
            self._hgPull(
             repo=repoDict['repo'],
             tag=repoDict.get('tag', 'default'),
             dirName=repoDict.get('dirName', None),
             parentDir=absWorkDir
            )

        locales = self.queryLocales()
        for locale in locales:
            self._hgPull(
             repo="%s/%s" % (hgL10nBase, locale),
             tag=hgL10nTag,
             parentDir=absL10nDir
            )

    def compareLocales(self):
        if not self.queryAction("compareLocales"):
            self.info("Skipping compare-locales step.")
            return
        self.info("Comparing locales.")
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")

    def repack(self):
        if not self.queryAction("repack"):
            self.info("Skipping repack step.")
            return
        self.info("Repacking.")

    def upload(self):
        if not self.queryAction("upload"):
            self.info("Skipping upload step.")
            return
        self.info("Uploading.")

    def processCommand(self, **kwargs):
        return kwargs

# MaemoMultiLocaleRepack {{{1
class MaemoMultiLocaleRepack(MultiLocaleRepack):
    configOptions = MultiLocaleRepack.configOptions + [[
     ["--debName",],
     {"action": "store",
      "dest": "debName",
      "type": "string",
      "help": "Specify the name of the deb"
     }
    ],[
     ["--sboxTarget",],
     {"action": "store",
      "dest": "sboxTarget",
      "type": "choice",
      "choices": ["FREMANTLE_ARMEL", "CHINOOK-ARMEL-2007"],
      "default": "FREMANTLE_ARMEL",
      "help": "Specify the scratchbox target"
     }
    ],[
     ["--sboxHome",],
     {"action": "store",
      "dest": "sboxHome",
      "type": "string",
      "default": "/scratchbox/users/cltbld/home/cltbld",
      "help": "Specify the scratchbox user home directory"
     }
    ],[
     ["--sboxPath",],
     {"action": "store",
      "dest": "sboxPath",
      "type": "string",
      "default": "/scratchbox/moz_scratchbox",
      "help": "Specify the scratchbox executable"
     }
    ],[
     ["--mobileRepo",],
     {"action": "store",
      "dest": "hgMobileRepo",
      "type": "string",
      "help": "Specify the mobile repo"
     }
    ],[
     ["--mobileTag",],
     {"action": "store",
      "dest": "hgMobileTag",
      "type": "string",
      "help": "Specify the mobile tag"
     }
    ]]

    def __init__(self, **kwargs):
        MultiLocaleRepack.__init__(self, **kwargs)

    def pull(self):
        hgMozillaRepo = self.queryVar("hgMozillaRepo")
        hgMozillaTag = self.queryVar("hgMozillaTag")
        hgCompareLocalesRepo = self.queryVar("hgCompareLocalesRepo")
        hgCompareLocalesTag = self.queryVar("hgCompareLocalesTag")
        hgMobileRepo = self.queryVar("hgMobileRepo")
        hgMobileTag = self.queryVar("hgMobileTag")
        repos = [{
            'repo': hgMozillaRepo,
            'tag': hgMozillaTag,
            'dirName': 'mozilla',
        },{
            'repo': hgMobileRepo,
            'tag': hgMobileTag,
            'dirName': 'mozilla/mobile',
        },{
            'repo': hgCompareLocalesRepo,
            'tag': hgCompareLocalesTag,
            'dirName': 'compare-locales',
        }]
        MultiLocaleRepack.pull(self, repos=repos)

    def processCommand(self, **kwargs):
        return kwargs



# __main__ {{{1
if __name__ == '__main__':
    maemoRepack = MaemoMultiLocaleRepack()
    maemoRepack.run()
