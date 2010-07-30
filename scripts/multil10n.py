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
from Log import SimpleFileLogger, BasicFunctions, SshErrorRegex, HgErrorRegex, PythonErrorRegex

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
                              allActions=['clobber', 'pull', 'setup',
                                          'compareLocales',
                                          'repack', 'upload'],
                              requireConfigFile=requireConfigFile)
        self.failures = []
        self.locales = None

    def run(self):
        self.clobber()
        self.pull()
        self.setup()
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
            baseWorkDir = self.queryVar("baseWorkDir")
            workDir = self.queryVar("workDir")
            localesFile = os.path.join(baseWorkDir, workDir,
              self.queryVar("localesFile"))
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
            hgConfigsRepo = self.queryVar("hgConfigsRepo")
            hgConfigsTag = self.queryVar("hgConfigsTag")
            repos = [{
                'repo': hgMozillaRepo,
                'tag': hgMozillaTag,
                'dirName': 'mozilla',
            },{
                'repo': hgCompareLocalesRepo,
                'tag': hgCompareLocalesTag,
                'dirName': 'compare-locales',
            },{
                'repo': hgConfigsRepo,
                'tag': hgConfigsTag,
                'dirName': 'configs',
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
             repo=os.path.join(hgL10nBase, locale),
             tag=hgL10nTag,
             parentDir=absL10nDir
            )

    def setup(self):
        if not self.queryAction("setup"):
            self.info("Skipping setup step.")
            return
        self.info("Setting up.")
        workDir = self.queryVar("workDir")
        baseWorkDir = self.queryVar("baseWorkDir")
        mozconfig = self.queryVar("mozconfig")
        localesDir = self.queryVar("localesDir")
        enUsBinaryUrl = self.queryVar("enUsBinaryUrl")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        absLocalesDir = os.path.join(absWorkDir, localesDir)

        self.chdir(absWorkDir)
        self.copyfile(mozconfig, os.path.join("mozilla", ".mozconfig"))

        # TODO error checking
        command = "bash -c autoconf-2.13"
        self.runCommand(command, cwd=os.path.join(absWorkDir, 'mozilla'))
        self.runCommand(command, cwd=os.path.join(absWorkDir, 'mozilla',
                                                  'js', 'src'))
        self._configure()
        command = "make"
        self.processCommand(command=command,
                            cwd=os.path.join(absWorkDir, "mozilla", "config"))
        command = "make wget-en-US EN_US_BINARY_URL=%s" % enUsBinaryUrl
        self.processCommand(command=command, cwd=absLocalesDir)

        self._getInstaller()

    def compareLocales(self):
        if not self.queryAction("compareLocales"):
            self.info("Skipping compare-locales step.")
            return
        self.info("Comparing locales.")
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        localesDir = self.queryVar("localesDir")
        mergeDir = "merged"
        absWorkDir = os.path.join(baseWorkDir, workDir)
        absLocalesDir = os.path.join(absWorkDir, localesDir)
        locales = self.queryLocales()
        compareLocalesScript = os.path.join("..", "..", "..", "compare-locales",
                                            "scripts", "compare-locales")
        compareLocalesEnv = os.environ.copy()
        compareLocalesEnv['PYTHONPATH'] = os.path.join('..', '..', '..',
                                                       'compare-locales', 'lib')
        CompareLocalesErrorRegex = list(PythonErrorRegex)

        for locale in locales:
            self.rmtree(os.path.join(absLocalesDir, mergeDir))
            command = "python %s -m %s l10n.ini %s %s" % (
              compareLocalesScript, mergeDir,
              os.path.join('..', '..', '..', 'l10n'), locale)
            self.runCommand(command, errorRegex=CompareLocalesErrorRegex,
                            cwd=absLocalesDir, env=compareLocalesEnv)

    def _configure(self):
        # TODO figure out if this works for desktop
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        configureApplication = self.queryVar("configureApplication")
        configureTarget = self.queryVar("configureTarget")

        command = "./configure --with-l10n-base=../l10n "
        if configureApplication:
            command += "--enable-application=%s " % configureApplication
        if configureTarget:
            command += "--target=%s " % configureTarget
        # TODO
        ConfigureErrorRegex = []
        self.processCommand(command=command, errorRegex=ConfigureErrorRegex,
                            cwd=os.path.join(absWorkDir, "mozilla"))

    def _getInstaller(self):
        # TODO
        pass

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
        return self.runCommand(**kwargs)

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
      "default": "/scratchbox/users/cltbld/home/cltbld/",
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
        self.debName = None

    def pull(self):
        hgMozillaRepo = self.queryVar("hgMozillaRepo")
        hgMozillaTag = self.queryVar("hgMozillaTag")
        hgCompareLocalesRepo = self.queryVar("hgCompareLocalesRepo")
        hgCompareLocalesTag = self.queryVar("hgCompareLocalesTag")
        hgMobileRepo = self.queryVar("hgMobileRepo")
        hgMobileTag = self.queryVar("hgMobileTag")
        hgConfigsRepo = self.queryVar("hgConfigsRepo")
        hgConfigsTag = self.queryVar("hgConfigsTag")
        repos = [{
            'repo': hgMozillaRepo,
            'tag': hgMozillaTag,
            'dirName': 'mozilla',
        },{
            'repo': hgMobileRepo,
            'tag': hgMobileTag,
            'dirName': os.path.join('mozilla', 'mobile'),
        },{
            'repo': hgCompareLocalesRepo,
            'tag': hgCompareLocalesTag,
            'dirName': 'compare-locales',
        },{
            'repo': hgConfigsRepo,
            'tag': hgConfigsTag,
            'dirName': 'configs',
        }]
        MultiLocaleRepack.pull(self, repos=repos)

    def setup(self):
        if not self.queryAction("setup"):
            self.info("Skipping setup step.")
            return
        MultiLocaleRepack.setup(self)

        sboxPath = self.queryVar("sboxPath")
        sboxTarget = self.queryVar("sboxTarget")
        self.runCommand("%s -p sb-conf select %s" % (sboxPath, sboxTarget))
        self.runCommand("%s -p \"echo -n TinderboxPrint: && sb-conf current | sed 's/ARMEL// ; s/_// ; s/-//'\"" % sboxPath)

    def queryDebName(self):
        if self.debName:
            return self.debName
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        localesDir = self.queryVar("localesDir")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        absLocalesDir = os.path.join(absWorkDir, localesDir)
        enUsBinaryUrl = self.queryVar("enUsBinaryUrl")

        command = "make wget-DEB_PKG_NAME EN_US_BINARY_URL=%s" % enUsBinaryUrl
        debName = self.processCommand(command=command, cwd=absLocalesDir,
                                      returnType='output')
        if debName:
            self.debName = debName
            return self.debName
        # error?

    def _getInstaller(self):
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        localesDir = self.queryVar("localesDir")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        absLocalesDir = os.path.join(absWorkDir, localesDir)
        enUsBinaryUrl = self.queryVar("enUsBinaryUrl")

        debName = self.queryDebName()

        command = "make wget-deb EN_US_BINARY_URL=%s DEB_PKG_NAME=%s DEB_BUILD_ARCH=armel" % (enUsBinaryUrl, debName)
        self.processCommand(command=command, cwd=absLocalesDir)

    def processCommand(self, **kwargs):
        sboxPath = self.queryVar("sboxPath")
        sboxHome = self.queryVar("sboxHome")
        command = '%s -p ' % sboxPath
        if 'cwd' in kwargs:
            command += '-d %s ' % kwargs['cwd'].replace(sboxHome, '')
            del kwargs['cwd']
        kwargs['command'] = '%s %s' % (command, kwargs['command'])
        return self.runCommand(**kwargs)



# __main__ {{{1
if __name__ == '__main__':
    maemoRepack = MaemoMultiLocaleRepack()
    maemoRepack.run()
