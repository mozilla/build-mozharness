#!/usr/bin/env python
"""multil10n.py

Our initial [successful] attempt at a multi-locale repack happened inside
of MaemoBuildFactory.  However, this was highly buildbot-intensive,
requiring runtime step truncation/creation with large amounts of build
properties that disallowed the use of "Force Build" for any multi-locale
nightly.

To improve things, we're moving the logic slave-side where a dedicated
slave can use its cycles determining which locales to repack.

Currently oriented towards Android multilocale, bug 563382.
"""

import hashlib
import os
import re
import sys

# load modules from parent dir
sys.path.insert(1, os.path.join(os.path.dirname(sys.path[0]), "lib"))

from base.config import parseConfigFile
from base.errors import SSHErrorRegexList, PythonErrorRegexList
from base.script import MercurialScript



# MultiLocaleRepack {{{1
class MultiLocaleRepack(MercurialScript):
    config_options = [[
     ["--locale",],
     {"action": "extend",
      "dest": "locales",
      "type": "string",
      "help": "Specify the locale(s) to repack"
     }
    ],[
     ["--merge-locales",],
     {"action": "store_true",
      "dest": "merge_locales",
      "default": False,
      "help": "Use default [en-US] if there are missing strings"
     }
    ],[
     ["--no-merge-locales",],
     {"action": "store_false",
      "dest": "merge_locales",
      "help": "Do not allow missing strings"
     }
    ],[
     ["--mozilla-repo",],
     {"action": "store",
      "dest": "hg_mozilla_repo",
      "type": "string",
      "help": "Specify the Mozilla repo"
     }
    ],[
     ["--mozilla-tag",],
     {"action": "store",
      "dest": "hg_mozilla_tag",
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
     ["--l10n-base",],
     {"action": "store",
      "dest": "hg_l10n_base",
      "type": "string",
      "help": "Specify the L10n repo base directory"
     }
    ],[
     ["--l10n-tag",],
     {"action": "store",
      "dest": "hg_l10n_tag",
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
     ["--compare-locales-repo",],
     {"action": "store",
      "dest": "hg_compare_locales_repo",
      "type": "string",
      "help": "Specify the compare-locales repo"
     }
    ],[
     ["--compare-locales-tag",],
     {"action": "store",
      "dest": "hg_compare_locales_tag",
      "type": "string",
      "help": "Specify the compare-locales tag"
     }
    ]]

    def __init__(self, require_config_file=True):
        MercurialScript.__init__(self, config_options=self.config_options,
                                 all_actions=['clobber', 'pull-build-source',
                                              'pull-locale-source',
                                              'build', 'package-en-US',
                                              'upload-en-US',
                                              'add-locales', 'package-multi',
                                              'upload-multi'],
                                 default_actions=['pull-locale-source',
                                                  'add-locales',
                                                  'package-multi'],
                                 require_config_file=require_config_file)
        self.locales = None
        c = self.config
        self.repos = [{
            'repo': c['hg_mozilla_repo'],
            'tag': c['hg_mozilla_tag'],
            'dir_name': c['mozilla_dir'],
        },{
            'repo': c['hg_configs_repo'],
            'tag': c['hg_configs_tag'],
            'dir_name': 'configs',
        }]
        # TODO: this references is_mobile, but we don't actually add any
        # of the --mobile-repo options.
        # I might need to subclass MultiLocaleRepack into
        # MobileMultiLocaleRepack, or make it able to do mobile
        # out of the box.
        if self.config['is_mobile']:
            self.repos.append({
                'repo': c['hg_mobile_repo'],
                'tag': c['hg_mobile_tag'],
                'dir_name': os.path.join(c['mozilla_dir'], 'mobile'),
            })

    def run(self):
        self.clobber()
        self.pull()
#        self.setup()
#        self.repack()
#        self.upload()
#        self.summary()

    def clobber(self):
        if 'clobber' not in self.actions:
            self.actionMessage("Skipping clobber step.")
            return
        self.actionMessage("Clobbering.")
        c = self.config
        path = os.path.join(c['base_work_dir'], c['work_dir'])
        if os.path.exists(path):
            self.rmtree(path, errorLevel='fatal')

    def queryLocales(self):
        if self.locales:
            return self.locales
        c = self.config
        locales = c.get("locales", None)
        ignore_locales = c.get("ignore_locales", None)
        if not locales:
            locales = []
            locales_file = os.path.join(c['base_work_dir'], c['work_dir'],
                                        c['locales_file'])
            if locales_file.endswith(".json"):
                locales_json = parseConfigFile(locales_file)
                locales = locales_json.keys()
            else:
                fh = open(locales_file)
                locales = fh.read().split()
                fh.close()
            self.debug("Found the locales %s in %s." % (locales, locales_file))
        if ignore_locales:
            for locale in ignore_locales:
                if locale in locales:
                    self.debug("Ignoring locale %s." % locale)
                    locales.remove(locale)
        if locales:
            self.locales = locales
            return self.locales

    def pull(self):
        c = self.config
        abs_work_dir = os.path.join(c['base_work_dir'],
                                    c['work_dir'])
        # Chicken/egg: need to pull repos to determine locales.
        # Solve by pulling non-locale repos first.
        if 'pull-build-source' not in self.actions:
            self.actionMessage("Skipping pull step.")
        else:
            self.actionMessage("Pulling.")
            self.mkdir_p(abs_work_dir)
            for repo_dict in repos:
                self.scmCheckout(
                 hg_repo=repo_dict['repo'],
                 tag=repo_dict['tag'],
                 dir_name=repo_dict.get('dir_name', None),
                 parent_dir=abs_work_dir
                )

        if 'pull-locale-source' not in self.actions:
            self.actionMessage("Skipping pull locale source step.")
        else:
            self.actionMessage("Pulling locale source.")
            # compare-locales
            self.scmCheckout(
             hg_repo=c['hg_compare_locales_repo'],
             tag=c['hg_compare_locales_tag'],
             dir_name='compare-locales',
             parent_dir=abs_work_dir
            )
            # locale repos
            abs_l10n_dir = os.path.join(abs_work_dir, c['l10n_dir'])
            self.mkdir_p(abs_l10n_dir)
            locales = self.queryLocales()
            for locale in locales:
                self.scmCheckout(
                 hg_repo=os.path.join(c['hg_l10n_base'], locale),
                 tag=c['hg_l10n_tag'],
                 parent_dir=abs_l10n_dir
                )

    def setup(self, check_action=True):
        if check_action:
            # We haven't been called from a child object.
            if 'setup' not in self.actions:
                self.actionMessage("Skipping setup step.")
                return
            self.actionMessage("Setting up.")
        c = self.config
        abs_work_dir = os.path.join(c['base_work_dir'], c['work_dir'])
        abs_objdir = os.path.join(abs_work_dir, c['mozilla_dir'], c['objdir'])
        abs_locales_dir = os.path.join(abs_objdir, c['locales_dir'])
        abs_branding_dir = os.path.join(abs_objdir, c['branding_dir'])

        self.chdir(abs_work_dir)
        self.copyfile(c['mozconfig'], os.path.join(c['mozilla_dir'], "mozconfig"))

        self.rmtree(os.path.join(abs_objdir, "dist"))

    def _getInstaller(self):
        # TODO
        pass

    def _updateRevisions(self):
        # TODO
        pass

    def repack(self):
        if 'repack' not in self.actions:
            self.actionMessage("Skipping repack step.")
            return
        self.actionMessage("Repacking.")
        c = self.config
        merge_dir = "merged"
        abs_work_dir = os.path.join(c['base_work_dir'], c['work_dir'])
        abs_locales_dir = os.path.join(abs_work_dir, c['mozilla_dir'],
                                       c['objdir'], c['locales_dir'])
        abs_locales_src_dir = os.path.join(abs_work_dir, c['mozilla_dir'],
                                           c['locales_dir'])
        abs_merge_dir = os.path.join(abs_locales_dir, merge_dir)
        locales = self.queryLocales()
        compare_locales_script = os.path.join("..", "..", "..",
                                              "compare-locales",
                                              "scripts", "compare-locales")
        compare_locales_env = os.environ.copy()
        compare_locales_env['PYTHONPATH'] = os.path.join('..', '..', '..',
                                                         'compare-locales', 'lib')
        compare_locales_error_regex_list = list(PythonErrorRegexList)

        for locale in locales:
            self.rmtree(os.path.join(abs_locales_dir, merge_dir))
            # TODO more error checking
            command = "python %s -m %s l10n.ini %s %s" % (
              compare_locales_script, abs_merge_dir,
              os.path.join('..', '..', '..', c['l10n_dir']), locale)
            self.runCommand(command, error_regex_list=compare_locales_error_regex_list,
                            cwd=abs_locales_src_dir, env=compare_locales_env)
            for step in ("chrome", "libs"):
                command = 'make %s-%s L10NBASEDIR=../../../../%s' % (step, locale, c['l10n_dir'])
                if c['merge_locales']:
                    command += " LOCALE_MERGEDIR=%s" % os.path.join(abs_locales_dir, merge_dir)
                self._processCommand(command=command, cwd=abs_locales_dir)
        self._repackage()

    def _repackage(self):
        # TODO
        pass

    def upload(self):
        if 'upload' not in self.actions:
            self.actionMessage("Skipping upload step.")
            return
        self.actionMessage("Uploading.")
        # TODO

    def _processCommand(self, **kwargs):
        return self.runCommand(**kwargs)

# __main__ {{{1
if __name__ == '__main__':
    multiLocaleRepack = MultiLocaleRepack()
    multiLocaleRepack.run()
