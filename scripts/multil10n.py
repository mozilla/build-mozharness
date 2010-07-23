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
                              allActions=['clobber', 'pull', 'setup',
                                          'repack', 'upload'],
                              requireConfigFile=requireConfigFile)
        self.failures = []

    def run(self):
        self.clobber()
        if self.failures:
            self.error("%s failures: %s" % (self.__class__.__name__,
                                            self.failures))

    def clobber(self):
        if not self.queryAction('clobber'):
            self.info("Skipping clobber step.")
            return
        self.info("Clobbering.")
        baseWorkDir = self.queryVar("baseWorkDir", os.getcwd())
        workDir = self.queryVar("workDir")
        path = os.path.join(baseWorkDir, workDir)
        if os.path.exists(path):
            self.rmtree(path, errorLevel='fatal')

    def processCommand(self, **kwargs):
        return kwargs

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

    def processCommand(self, **kwargs):
        return kwargs



# __main__ {{{1
if __name__ == '__main__':
    multiRepack = MultiLocaleRepack()
#    multiRepack.run()
    print multiRepack.dumpConfig()
    maemoRepack = MaemoMultiLocaleRepack()
    print maemoRepack.dumpConfig()
