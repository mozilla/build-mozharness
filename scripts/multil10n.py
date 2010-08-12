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

import hashlib
import os
import re
import sys

# load modules from parent dir
sys.path[0] = os.path.dirname(sys.path[0])

import log
reload(log)
from log import SimpleFileLogger, BasicFunctions, SSHErrorRegexList, HgErrorRegexList, PythonErrorRegexList

import config
reload(config)
from config import SimpleConfig



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
     ["--mozilla-dir",],
     {"action": "store",
      "dest": "mozilla_dir",
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
     ["--l10n-dir",],
     {"action": "store",
      "dest": "l10n_dir",
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
        base_work_dir = self.queryVar("base_work_dir")
        work_dir = self.queryVar("work_dir")
        path = os.path.join(base_work_dir, work_dir)
        if os.path.exists(path):
            self.rmtree(path, errorLevel='fatal')

    def queryLocales(self):
        if self.locales:
            return self.locales
        locales = self.queryVar("locales")
        ignoreLocales = self.queryVar("ignoreLocales")
        if not locales:
            locales = []
            base_work_dir = self.queryVar("base_work_dir")
            work_dir = self.queryVar("work_dir")
            localesFile = os.path.join(base_work_dir, work_dir,
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

    def _hgPull(self, repo, parent_dir, tag="default", dirName=None,
                haltOnFailure=True):
        if not dirName:
            dirName = os.path.basename(repo)
        if not os.path.exists(os.path.join(parent_dir, dirName)):
            command = "hg clone %s %s" % (repo, dirName)
        else:
            command = "hg --cwd %s pull" % (dirName)
        self.runCommand(command, cwd=parent_dir, haltOnFailure=haltOnFailure,
                        errorRegexList=HgErrorRegexList)
        command = "hg --cwd %s update -C -r %s" % (dirName, tag)
        self.runCommand(command, cwd=parent_dir, haltOnFailure=haltOnFailure,
                        errorRegexList=HgErrorRegexList)

    def pull(self, repos=None):
        base_work_dir = self.queryVar("base_work_dir")
        work_dir = self.queryVar("work_dir")
        abs_work_dir = os.path.join(base_work_dir, work_dir)
        hgL10nBase = self.queryVar("hgL10nBase")
        hgL10nTag = self.queryVar("hgL10nTag")
        l10n_dir = self.queryVar("l10n_dir")
        if not repos:
            hgMozillaRepo = self.queryVar("hgMozillaRepo")
            hgMozillaTag = self.queryVar("hgMozillaTag")
            mozilla_dir = self.queryVar("mozilla_dir")
            hgCompareLocalesRepo = self.queryVar("hgCompareLocalesRepo")
            hgCompareLocalesTag = self.queryVar("hgCompareLocalesTag")
            hgConfigsRepo = self.queryVar("hgConfigsRepo")
            hgConfigsTag = self.queryVar("hgConfigsTag")
            repos = [{
                'repo': hgMozillaRepo,
                'tag': hgMozillaTag,
                'dirName': mozilla_dir,
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
            self.mkdir_p(abs_work_dir)
            for repoDict in repos:
                self._hgPull(
                 repo=repoDict['repo'],
                 tag=repoDict.get('tag', 'default'),
                 dirName=repoDict.get('dirName', None),
                 parent_dir=abs_work_dir
                )

        if not self.queryAction('pullLocales'):
            self.info("Skipping pull locales step.")
        else:
            self.info("Pulling locales.")
            abs_l10n_dir = os.path.join(abs_work_dir, l10n_dir)
            self.mkdir_p(abs_l10n_dir)
            locales = self.queryLocales()
            for locale in locales:
                self._hgPull(
                 repo=os.path.join(hgL10nBase, locale),
                 tag=hgL10nTag,
                 parent_dir=abs_l10n_dir
                )

    def setup(self, checkAction=True):
        if checkAction:
            # We haven't been called from a child object.
            if not self.queryAction("setup"):
                self.info("Skipping setup step.")
                return
            self.info("Setting up.")
        work_dir = self.queryVar("work_dir")
        base_work_dir = self.queryVar("base_work_dir")
        mozconfig = self.queryVar("mozconfig")
        locales_dir = self.queryVar("locales_dir")
        enUsBinaryUrl = self.queryVar("enUsBinaryUrl")
        mozilla_dir = self.queryVar("mozilla_dir")
        branding_dir = self.queryVar("branding_dir")
        objdir = self.queryVar("objdir")
        abs_work_dir = os.path.join(base_work_dir, work_dir)
        absObjdir = os.path.join(abs_work_dir, mozilla_dir, objdir)
        abs_locales_dir = os.path.join(absObjdir, locales_dir)
        abs_branding_dir = os.path.join(absObjdir, branding_dir)

        self.chdir(abs_work_dir)
        self.copyfile(mozconfig, os.path.join(mozilla_dir, ".mozconfig"))

        self.rmtree(os.path.join(abs_work_dir, mozilla_dir, objdir, "dist"))

        # TODO error checking
        command = "make -f client.mk configure"
        self._processCommand(command=command, cwd=os.path.join(abs_work_dir, mozilla_dir))
        command = "make"
        self._processCommand(command=command, cwd=os.path.join(absObjdir, "config"))
        command = "make wget-en-US EN_US_BINARY_URL=%s" % enUsBinaryUrl
        self._processCommand(command=command, cwd=abs_locales_dir)

        self._getInstaller()
        command = "make unpack"
        self._processCommand(command=command, cwd=abs_locales_dir)
        self._updateRevisions()
        command = "make"
        self._processCommand(command=command, cwd=abs_branding_dir)

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
        base_work_dir = self.queryVar("base_work_dir")
        work_dir = self.queryVar("work_dir")
        locales_dir = self.queryVar("locales_dir")
        mozilla_dir = self.queryVar("mozilla_dir")
        objdir = self.queryVar("objdir")
        l10n_dir = self.queryVar("l10n_dir")
        mergeLocales = self.queryVar("mergeLocales")
        merge_dir = "merged"
        abs_work_dir = os.path.join(base_work_dir, work_dir)
        abs_locales_dir = os.path.join(abs_work_dir, mozilla_dir, objdir, locales_dir)
        abs_locales_src_dir = os.path.join(abs_work_dir, mozilla_dir, locales_dir)
        abs_merge_dir = os.path.join(abs_locales_dir, merge_dir)
        locales = self.queryLocales()
        compareLocalesScript = os.path.join("..", "..", "..",
                                            "compare-locales",
                                            "scripts", "compare-locales")
        compareLocalesEnv = os.environ.copy()
        compareLocalesEnv['PYTHONPATH'] = os.path.join('..', '..', '..',
                                                       'compare-locales', 'lib')
        CompareLocalesErrorRegexList = list(PythonErrorRegexList)

        for locale in locales:
            self.rmtree(os.path.join(abs_locales_dir, merge_dir))
            # TODO more error checking
            command = "python %s -m %s l10n.ini %s %s" % (
              compareLocalesScript, abs_merge_dir,
              os.path.join('..', '..', '..', l10n_dir), locale)
            self.runCommand(command, errorRegexList=CompareLocalesErrorRegexList,
                            cwd=abs_locales_src_dir, env=compareLocalesEnv)
            for step in ("chrome", "libs"):
                command = 'make %s-%s L10NBASEDIR=../../../../%s' % (step, locale, l10n_dir)
                if mergeLocales:
                    command += " LOCALE_MERGEDIR=%s" % os.path.join(abs_locales_dir, merge_dir)
                self._processCommand(command=command, cwd=abs_locales_dir)
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
        mozilla_dir = self.queryVar("mozilla_dir")
        hgCompareLocalesRepo = self.queryVar("hgCompareLocalesRepo")
        hgCompareLocalesTag = self.queryVar("hgCompareLocalesTag")
        hgMobileRepo = self.queryVar("hgMobileRepo")
        hgMobileTag = self.queryVar("hgMobileTag")
        hgConfigsRepo = self.queryVar("hgConfigsRepo")
        hgConfigsTag = self.queryVar("hgConfigsTag")
        repos = [{
            'repo': hgMozillaRepo,
            'tag': hgMozillaTag,
            'dirName': mozilla_dir,
        },{
            'repo': hgMobileRepo,
            'tag': hgMobileTag,
            'dirName': os.path.join(mozilla_dir, 'mobile'),
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
        base_work_dir = self.queryVar("base_work_dir")
        work_dir = self.queryVar("work_dir")
        mozilla_dir = self.queryVar("mozilla_dir")
        objdir = self.queryVar("objdir")
        locales_dir = self.queryVar("locales_dir")
        abs_work_dir = os.path.join(base_work_dir, work_dir)
        abs_locales_dir = os.path.join(abs_work_dir, mozilla_dir, objdir, locales_dir)
        enUsBinaryUrl = self.queryVar("enUsBinaryUrl")

        command = "make wget-DEB_PKG_NAME EN_US_BINARY_URL=%s" % enUsBinaryUrl
        self.debName = self._processCommand(command=command, cwd=abs_locales_dir,
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
        base_work_dir = self.queryVar("base_work_dir")
        work_dir = self.queryVar("work_dir")
        mozilla_dir = self.queryVar("mozilla_dir")
        objdir = self.queryVar("objdir")
        locales_dir = self.queryVar("locales_dir")
        abs_work_dir = os.path.join(base_work_dir, work_dir)
        abs_locales_dir = os.path.join(abs_work_dir, mozilla_dir, objdir, locales_dir)
        enUsBinaryUrl = self.queryVar("enUsBinaryUrl")

        debName = self.queryDebName()

        command = "make wget-deb EN_US_BINARY_URL=%s DEB_PKG_NAME=%s DEB_BUILD_ARCH=armel" % (enUsBinaryUrl, debName)
        self._processCommand(command=command, cwd=abs_locales_dir)

    def _updateRevisions(self):
        base_work_dir = self.queryVar("base_work_dir")
        work_dir = self.queryVar("work_dir")
        locales_dir = self.queryVar("locales_dir")
        objdir = self.queryVar("objdir")
        mozilla_dir = self.queryVar("mozilla_dir")
        abs_work_dir = os.path.join(base_work_dir, work_dir)
        abs_locales_dir = os.path.join(abs_work_dir, mozilla_dir, objdir, locales_dir)

        command = "make ident"
        output = self._processCommand(command=command, cwd=abs_locales_dir,
                                      returnType='output')
        for line in output.split('\n'):
            if line.startswith('gecko_revision '):
                gecko_revision = line.split(' ')[-1]
            elif line.startswith('fennec_revision '):
                fennec_revision = line.split(' ')[-1]
        command = "hg up -C -r %s" % gecko_revision
        self.runCommand(command, cwd=os.path.join(abs_work_dir, mozilla_dir))
        command = "hg up -C -r %s" % fennec_revision
        self.runCommand(command, cwd=os.path.join(abs_work_dir, mozilla_dir,
                                                  "mobile"))

    def _repackage(self):
        base_work_dir = self.queryVar("base_work_dir")
        work_dir = self.queryVar("work_dir")
        mozilla_dir = self.queryVar("mozilla_dir")
        objdir = self.queryVar("objdir")
        abs_work_dir = os.path.join(base_work_dir, work_dir)
        absObjdir = os.path.join(abs_work_dir, mozilla_dir, objdir)
        debName = self.queryDebName()
        debPackageVersion = self.queryDebPackageVersion()
        tmp_deb_dir = os.path.join("dist", "tmp.deb")
        abs_tmp_deb_dir = os.path.join(absObjdir, tmp_deb_dir)

        # TODO error checking
#        command = "make package AB_CD=multi"
#        self._processCommand(command=command, cwd=absObjdir)
        command = "make deb AB_CD=multi DEB_PKG_NAME=%s DEB_PKG_VERSION=%s" % (debName, debPackageVersion)
        self._processCommand(command=command, cwd=absObjdir)

        self.rmtree(os.path.join(abs_tmp_deb_dir))
        self.mkdir_p(os.path.join(abs_tmp_deb_dir, "DEBIAN"))
        arErrorRegexList = [{
         'substr': 'No such file or directory', 'level': 'error'
        },{
         'substr': 'Cannot write: Broken pipe', 'level': 'error'
        }]
        command = "ar p mobile/locales/%s control.tar.gz | tar zxv -C %s/DEBIAN" % \
          (debName, tmp_deb_dir)
        self.runCommand(command=command, cwd=absObjdir,
                        errorRegexList=arErrorRegexList)
        command = "ar p mobile/locales/%s data.tar.gz | tar zxv -C %s" % \
          (debName, tmp_deb_dir)
        self.runCommand(command=command, cwd=absObjdir,
                        errorRegexList=arErrorRegexList)
        command = "ar p mobile/%s data.tar.gz | tar zxv -C %s" % \
          (debName, tmp_deb_dir)
        self.runCommand(command=command, cwd=absObjdir,
                        errorRegexList=arErrorRegexList)

        # fix DEBIAN/md5sums
        self.info("Creating md5sums file...")
        command = "find * -type f | grep -v DEBIAN"
        fileList = self.getOutputFromCommand(command=command, cwd=abs_tmp_deb_dir).split('\n')
        md5File = os.path.join(abs_tmp_deb_dir, "DEBIAN", "md5sums")
        md5FH = open(md5File, 'w')
        for fileName in fileList:
            contents = open(os.path.join(abs_tmp_deb_dir, fileName)).read()
            md5sum = hashlib.md5(contents).hexdigest()
            md5FH.write("%s  %s\n" % (md5sum, fileName))
        md5FH.close()

        command = "dpkg-deb -b %s dist/%s" % (abs_tmp_deb_dir, debName)
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
            if 'errorRegexList' in kwargs:
                kwargs['errorRegexList'] = PythonErrorRegexList + kwargs['errorRegexList']
            else:
                kwargs['errorRegexList'] = PythonErrorRegexList
            return self.runCommand(**kwargs)
        else:
            del(kwargs['returnType'])
            return self.getOutputFromCommand(**kwargs)



# __main__ {{{1
if __name__ == '__main__':
    maemoRepack = MaemoMultiLocaleRepack()
    maemoRepack.run()
