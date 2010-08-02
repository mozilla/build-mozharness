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
import re
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
     ["--mozillaDir",],
     {"action": "store",
      "dest": "mozillaDir",
      "type": "string",
      "default": "mozilla",
      "help": "Specify the Mozilla dir name"
     }
    ],[
     ["--objdir",],
     {"action": "store",
      "dest": "objdir",
      "type": "string",
      "default": "objdir",
      "help": "Specify the objdir"
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
     ["--l10nDir",],
     {"action": "store",
      "dest": "l10nDir",
      "type": "string",
      "default": "l10n",
      "help": "Specify the l10n dir name"
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
                              allActions=['clobber', 'pull', 'pullLocales',
                                          'setup', 'repack', 'upload'],
                              requireConfigFile=requireConfigFile)
        self.failures = []
        self.locales = None

    def run(self):
        self.clobber()
        self.pull()
        self.setup()
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
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        hgL10nBase = self.queryVar("hgL10nBase")
        hgL10nTag = self.queryVar("hgL10nTag")
        l10nDir = self.queryVar("l10nDir")
        if not repos:
            hgMozillaRepo = self.queryVar("hgMozillaRepo")
            hgMozillaTag = self.queryVar("hgMozillaTag")
            mozillaDir = self.queryVar("mozillaDir")
            hgCompareLocalesRepo = self.queryVar("hgCompareLocalesRepo")
            hgCompareLocalesTag = self.queryVar("hgCompareLocalesTag")
            hgConfigsRepo = self.queryVar("hgConfigsRepo")
            hgConfigsTag = self.queryVar("hgConfigsTag")
            repos = [{
                'repo': hgMozillaRepo,
                'tag': hgMozillaTag,
                'dirName': mozillaDir,
            },{
                'repo': hgCompareLocalesRepo,
                'tag': hgCompareLocalesTag,
                'dirName': 'compare-locales',
            },{
                'repo': hgConfigsRepo,
                'tag': hgConfigsTag,
                'dirName': 'configs',
            }]

        # Chicken/egg: need to pull repos to determine locales.
        # Solve by pulling non-locale repos first.
        if not self.queryAction('pull'):
            self.info("Skipping pull step.")
        else:
            self.info("Pulling.")
            for repoDict in repos:
                self._hgPull(
                 repo=repoDict['repo'],
                 tag=repoDict.get('tag', 'default'),
                 dirName=repoDict.get('dirName', None),
                 parentDir=absWorkDir
                )

        if not self.queryAction('pullLocales'):
            self.info("Skipping pull locales step.")
        else:
            self.info("Pulling locales.")
            absL10nDir = os.path.join(absWorkDir, l10nDir)
            self.mkdir_p(absL10nDir)
            locales = self.queryLocales()
            for locale in locales:
                self._hgPull(
                 repo=os.path.join(hgL10nBase, locale),
                 tag=hgL10nTag,
                 parentDir=absL10nDir
                )

    def setup(self, checkAction=True):
        if checkAction:
            # We haven't been called from a child object.
            if not self.queryAction("setup"):
                self.info("Skipping setup step.")
                return
            self.info("Setting up.")
        workDir = self.queryVar("workDir")
        baseWorkDir = self.queryVar("baseWorkDir")
        mozconfig = self.queryVar("mozconfig")
        localesDir = self.queryVar("localesDir")
        enUsBinaryUrl = self.queryVar("enUsBinaryUrl")
        mozillaDir = self.queryVar("mozillaDir")
        brandingDir = self.queryVar("brandingDir")
        objdir = self.queryVar("objdir")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        absObjdir = os.path.join(absWorkDir, mozillaDir, objdir)
        absLocalesDir = os.path.join(absObjdir, localesDir)
        absBrandingDir = os.path.join(absObjdir, brandingDir)

        self.chdir(absWorkDir)
        self.copyfile(mozconfig, os.path.join(mozillaDir, ".mozconfig"))

        self.rmtree(os.path.join(absWorkDir, mozillaDir, objdir, "dist"))

        # TODO error checking
        command = "make -f client.mk configure"
        self._processCommand(command=command, cwd=os.path.join(absWorkDir, mozillaDir))
        command = "make"
        self._processCommand(command=command, cwd=os.path.join(absObjdir, "config"))
        command = "make wget-en-US EN_US_BINARY_URL=%s" % enUsBinaryUrl
        self._processCommand(command=command, cwd=absLocalesDir)

        self._getInstaller()
        command = "make unpack"
        self._processCommand(command=command, cwd=absLocalesDir)
        self._updateRevisions()
        command = "make"
        self._processCommand(command=command, cwd=absBrandingDir)

    def _getInstaller(self):
        # TODO
        pass

    def _updateRevisions(self):
        # TODO
        pass

    def repack(self):
        if not self.queryAction("repack"):
            self.info("Skipping repack step.")
            return
        self.info("Repacking.")
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        localesDir = self.queryVar("localesDir")
        mozillaDir = self.queryVar("mozillaDir")
        objdir = self.queryVar("objdir")
        l10nDir = self.queryVar("l10nDir")
        mergeLocales = self.queryVar("mergeLocales")
        mergeDir = "merged"
        absWorkDir = os.path.join(baseWorkDir, workDir)
        absLocalesDir = os.path.join(absWorkDir, mozillaDir, objdir, localesDir)
        absLocalesSrcDir = os.path.join(absWorkDir, mozillaDir, localesDir)
        absMergeDir = os.path.join(absLocalesDir, mergeDir)
        locales = self.queryLocales()
        compareLocalesScript = os.path.join("..", "..", "..",
                                            "compare-locales",
                                            "scripts", "compare-locales")
        compareLocalesEnv = os.environ.copy()
        compareLocalesEnv['PYTHONPATH'] = os.path.join('..', '..', '..',
                                                       'compare-locales', 'lib')
        CompareLocalesErrorRegex = list(PythonErrorRegex)

        for locale in locales:
            self.rmtree(os.path.join(absLocalesDir, mergeDir))
            # TODO more error checking
            command = "python %s -m %s l10n.ini %s %s" % (
              compareLocalesScript, absMergeDir,
              os.path.join('..', '..', '..', l10nDir), locale)
            self.runCommand(command, errorRegex=CompareLocalesErrorRegex,
                            cwd=absLocalesSrcDir, env=compareLocalesEnv)
            for step in ("chrome", "libs"):
                command = 'make %s-%s L10NBASEDIR=../../../../%s' % (step, locale, l10nDir)
                if mergeLocales:
                    command += " LOCALE_MERGEDIR=%s" % os.path.join(absLocalesDir, mergeDir)
                self._processCommand(command=command, cwd=absLocalesDir)
        self._repackage()

    def _repackage(self):
        # TODO
        pass

    def upload(self):
        if not self.queryAction("upload"):
            self.info("Skipping upload step.")
            return
        self.info("Uploading.")

    def _processCommand(self, **kwargs):
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
     ["--sboxRoot",],
     {"action": "store",
      "dest": "sboxRoot",
      "type": "string",
      "default": "/scratchbox/users/cltbld",
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
        self.debPackageVersion = None

    def pull(self):
        hgMozillaRepo = self.queryVar("hgMozillaRepo")
        hgMozillaTag = self.queryVar("hgMozillaTag")
        mozillaDir = self.queryVar("mozillaDir")
        hgCompareLocalesRepo = self.queryVar("hgCompareLocalesRepo")
        hgCompareLocalesTag = self.queryVar("hgCompareLocalesTag")
        hgMobileRepo = self.queryVar("hgMobileRepo")
        hgMobileTag = self.queryVar("hgMobileTag")
        hgConfigsRepo = self.queryVar("hgConfigsRepo")
        hgConfigsTag = self.queryVar("hgConfigsTag")
        repos = [{
            'repo': hgMozillaRepo,
            'tag': hgMozillaTag,
            'dirName': mozillaDir,
        },{
            'repo': hgMobileRepo,
            'tag': hgMobileTag,
            'dirName': os.path.join(mozillaDir, 'mobile'),
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
        self.info("Setting up.")
        sboxPath = self.queryVar("sboxPath")
        sboxTarget = self.queryVar("sboxTarget")
        self.runCommand("%s -p sb-conf select %s" % (sboxPath, sboxTarget))
        self.runCommand("%s -p \"echo -n TinderboxPrint: && sb-conf current | sed 's/ARMEL// ; s/_// ; s/-//'\"" % sboxPath)
        MultiLocaleRepack.setup(self, checkAction=False)

    def queryDebName(self):
        if self.debName:
            return self.debName
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        mozillaDir = self.queryVar("mozillaDir")
        objdir = self.queryVar("objdir")
        localesDir = self.queryVar("localesDir")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        absLocalesDir = os.path.join(absWorkDir, mozillaDir, objdir, localesDir)
        enUsBinaryUrl = self.queryVar("enUsBinaryUrl")

        command = "make wget-DEB_PKG_NAME EN_US_BINARY_URL=%s" % enUsBinaryUrl
        self.debName = self._processCommand(command=command, cwd=absLocalesDir,
                                            haltOnFailure=True,
                                            returnType='output')
        return self.debName

    def queryDebPackageVersion(self):
        if self.debPackageVersion:
            return self.debPackageVersion
        debName = self.queryDebName()
        m = re.match(r'[^_]+_([^_]+)_', debName)
        self.debPackageVersion = m.groups()[0]
        return self.debPackageVersion

    def _getInstaller(self):
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        mozillaDir = self.queryVar("mozillaDir")
        objdir = self.queryVar("objdir")
        localesDir = self.queryVar("localesDir")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        absLocalesDir = os.path.join(absWorkDir, mozillaDir, objdir, localesDir)
        enUsBinaryUrl = self.queryVar("enUsBinaryUrl")

        debName = self.queryDebName()

        command = "make wget-deb EN_US_BINARY_URL=%s DEB_PKG_NAME=%s DEB_BUILD_ARCH=armel" % (enUsBinaryUrl, debName)
        self._processCommand(command=command, cwd=absLocalesDir)

    def _updateRevisions(self):
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        localesDir = self.queryVar("localesDir")
        objdir = self.queryVar("objdir")
        mozillaDir = self.queryVar("mozillaDir")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        absLocalesDir = os.path.join(absWorkDir, mozillaDir, objdir, localesDir)

        command = "make ident"
        output = self._processCommand(command=command, cwd=absLocalesDir,
                                      returnType='output')
        for line in output.split('\n'):
            if line.startswith('gecko_revision '):
                gecko_revision = line.split(' ')[-1]
            elif line.startswith('fennec_revision '):
                fennec_revision = line.split(' ')[-1]
        command = "hg up -C -r %s" % gecko_revision
        self.runCommand(command, cwd=os.path.join(absWorkDir, mozillaDir))
        command = "hg up -C -r %s" % fennec_revision
        self.runCommand(command, cwd=os.path.join(absWorkDir, mozillaDir,
                                                  "mobile"))

    def _repackage(self):
        baseWorkDir = self.queryVar("baseWorkDir")
        workDir = self.queryVar("workDir")
        mozillaDir = self.queryVar("mozillaDir")
        objdir = self.queryVar("objdir")
        absWorkDir = os.path.join(baseWorkDir, workDir)
        absObjdir = os.path.join(absWorkDir, mozillaDir, objdir)
        debName = self.queryDebName()
        tmpDebDir = os.path.join("dist", "tmp.deb")
        absTmpDebDir = os.path.join(absObjdir, tmpDebDir)

        # TODO error checking
        command = "make package AB_CD=multi"
        self._processCommand(command=command, cwd=absObjdir)
        command = "make deb AB_CD=multi"
        self._processCommand(command=command, cwd=absObjdir)

        # Ugh, get the binary bits from the en-US deb, and the multilocale
        # bits from the multi deb
        self.rmtree(os.path.join(absTmpDebDir))
        self.mkdir_p(os.path.join(absTmpDebDir, "DEBIAN"))
        arErrorRegex = [{
         'substr': 'Cannot write: Broken pipe', 'level': 'error'
        }]
        command = "ar p mobile/locales/%s control.tar.gz" % debName
        self._processCommand(command=command, cwd=absObjdir,
                             errorRegex=arErrorRegex)
        command = "tar zx control.tar.gz -C %s/DEBIAN" % tmpDebDir
        self._processCommand(command=command, cwd=absObjdir,
                             errorRegex=arErrorRegex)
        command = "ar p mobile/locales/%s data.tar.gz" % debName
        self._processCommand(command=command, cwd=absObjdir,
                             errorRegex=arErrorRegex)
        command = "tar zx data.tar.gz -C %s" % tmpDebDir
        self._processCommand(command=command, cwd=absObjdir,
                             errorRegex=arErrorRegex)
        command = "ar p mobile/%s data.tar.gz" % debName
        self._processCommand(command=command, cwd=absObjdir,
                             errorRegex=arErrorRegex)
        command = "tar zx data.tar.gz -C %s" % tmpDebDir
        self._processCommand(command=command, cwd=absObjdir,
                             errorRegex=arErrorRegex)
        command = "dpkg-deb -b %s dist/%s" % (absTmpDebDir, debName)
        self._processCommand(command=command, cwd=absObjdir)

    def _processCommand(self, **kwargs):
        sboxPath = self.queryVar("sboxPath")
        sboxHome = self.queryVar("sboxHome")
        sboxRoot = self.queryVar("sboxRoot")
        command = '%s ' % sboxPath
        if 'returnType' not in kwargs or kwargs['returnType'] != 'output':
            command += '-p '
        if 'cwd' in kwargs:
            command += '-d %s ' % kwargs['cwd'].replace(sboxHome, '')
            del kwargs['cwd']
        kwargs['command'] = '%s "%s"' % (command, kwargs['command'].replace(sboxRoot, ''))
        if 'returnType' not in kwargs or kwargs['returnType'] != 'output':
            if 'errorRegex' in kwargs:
                kwargs['errorRegex'] = PythonErrorRegex + kwargs['errorRegex']
            else:
                kwargs['errorRegex'] = PythonErrorRegex
            return self.runCommand(**kwargs)
        else:
            del(kwargs['returnType'])
            return self.getOutputFromCommand(**kwargs)



# __main__ {{{1
if __name__ == '__main__':
    maemoRepack = MaemoMultiLocaleRepack()
    maemoRepack.run()
