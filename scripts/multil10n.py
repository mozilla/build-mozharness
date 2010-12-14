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

TODO: finish work to make this a standalone runnable script.
"""

import hashlib
import os
import re
import sys

# load modules from parent dir
sys.path.insert(1, os.path.join(os.path.dirname(sys.path[0]), "lib"))

from base.config import parseConfigFile
from base.errors import SSHErrorList, PythonErrorList, MakefileErrorList
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
# TODO no package-en-US or upload-en-US here.
# which is fine; that'll be handled by buildbot factories for now, but we
# should add it later for completeness.
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
        },{
# TODO currently only needed for Android?
            'repo': c['hg_tools_repo'],
            'tag': c['hg_tools_tag'],
            'dir_name': 'tools',
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
        self.build()
        self.package(package_type='en-US')
#        self.upload(package_type='en-US')
        self.addLocales()
        self.package(package_type='multi')
#        self.upload(package_type='multi')

    def clobber(self):
        if 'clobber' not in self.actions:
            self.actionMessage("Skipping clobber step.")
            return
        self.actionMessage("Clobbering.")
        c = self.config
        if c['work_dir'] != '.':
            path = os.path.join(c['base_work_dir'], c['work_dir'])
            if os.path.exists(path):
                self.rmtree(path, error_level='fatal')
        # TODO what to do otherwise?

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
                # TODO this belongs in a shared function for releases.
                locales_json = parseConfigFile(locales_file)
                self.locale_dict = {}
                for locale in locales_json.keys():
                    if c['locales_platform'] in locales_json[locale]['platforms']:
                        locales.append(locale)
                        self.locale_dict[locale] = locales_json[locale]['revision']

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
            for repo_dict in self.repos:
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
                tag = c['hg_l10n_tag']
                if hasattr(self, 'locale_dict'):
                    tag = self.locale_dict[locale]
                self.scmCheckout(
                 hg_repo=os.path.join(c['hg_l10n_base'], locale),
                 tag=tag,
                 parent_dir=abs_l10n_dir
                )

    def build(self):
        if 'build' not in self.actions:
            self.actionMessage("Skipping build step.")
            return
        self.actionMessage("Building.")
        c = self.config
        abs_work_dir = os.path.join(c['base_work_dir'],
                                    c['work_dir'])
        abs_mozilla_dir = os.path.join(abs_work_dir, c['mozilla_dir'])
        self.copyfile(os.path.join(abs_work_dir, c['mozconfig']),
                      os.path.join(abs_mozilla_dir, 'mozconfig'),
                      error_level='fatal')
        command = "make -f client.mk build"
        # only a little ugly?
        env = c['java_env']
        if 'PATH' in env:
            env['PATH'] = env['PATH'] % {'PATH': os.environ['PATH']}
        self.runCommand(command, cwd=abs_mozilla_dir, env=env,
                        error_list=MakefileErrorList,
                        halt_on_failure=True)

    def addLocales(self):
        if 'add-locales' not in self.actions:
            self.actionMessage("Skipping add-locales step.")
            return
        self.actionMessage("Adding locales to the apk.")
        c = self.config
        locales = self.queryLocales()
        # TODO a lot of the lines of code here are determining paths.
        # Each of these action methods should be able to call a single
        # function that returns a dictionary of these that we can use
        # so we don't have to keep redefining them.
        abs_work_dir = os.path.join(c['base_work_dir'],
                                    c['work_dir'])
        merge_dir = "merged"
        abs_merge_dir = os.path.join(abs_work_dir, c['objdir'], merge_dir)
        abs_locales_dir = os.path.join(abs_work_dir, c['mozilla_dir'],
                                       c['objdir'], c['locales_dir'])
        abs_locales_src_dir = os.path.join(abs_work_dir, c['mozilla_dir'],
                                           c['locales_dir'])
        abs_l10n_dir = os.path.join(abs_work_dir, c['l10n_dir'])
        abs_compare_locales_dir = os.path.join(abs_work_dir, 'compare-locales')
        compare_locales_script = os.path.join(abs_compare_locales_dir, 'scripts',
                                              'compare-locales')
        compare_locales_env = os.environ.copy()
        compare_locales_env['PYTHONPATH'] = os.path.join(abs_compare_locales_dir,
                                                         'lib')
        compare_locales_error_list = list(PythonErrorList)

        for locale in locales:
            self.rmtree(abs_merge_dir)
            command = "python %s -m %s l10n.ini %s %s" % (compare_locales_script,
                      abs_merge_dir, abs_l10n_dir, locale)
            self.runCommand(command, error_list=compare_locales_error_list,
                            cwd=abs_locales_src_dir, env=compare_locales_env,
                            halt_on_failure=True)
            command = 'make chrome-%s L10NBASEDIR=%s' % (locale, abs_l10n_dir)
            if c['merge_locales']:
                command += " LOCALE_MERGEDIR=%s" % abs_merge_dir
                self.runCommand(command, cwd=abs_locales_dir,
                                error_list=MakefileErrorList,
                                halt_on_failure=True)

    def package(self, package_type='en-US'):
        if 'package-%s' % package_type not in self.actions:
            self.actionMessage("Skipping package-%s." % package_type)
            return
        self.actionMessage("Packaging %s." % package_type)
        c = self.config
        abs_work_dir = os.path.join(c['base_work_dir'],
                                    c['work_dir'])
        abs_objdir = os.path.join(abs_work_dir, c['mozilla_dir'], c['objdir'])
        command = "make package"
        # only a little ugly?
        env = c['java_env']
        if 'PATH' in env:
            env['PATH'] = env['PATH'] % {'PATH': os.environ['PATH']}
        if package_type == 'multi':
            command += " AB_CD=multi"
            env['MOZ_CHROME_MULTILOCALE'] = ' '.join(self.locales)
            self.info("MOZ_CHROME_MULTILOCALE is %s" % env['MOZ_CHROME_MULTILOCALE'])
        # TODO this is totally Android specific and needs to be either
        # moved into a child object or special cased. However, as this
        # class is currently Android only, here we go.
        if 'jarsigner' in c:
            # hm, this is pretty mozpass.py specific
            env['JARSIGNER'] = os.path.join(abs_work_dir, c['jarsigner'])
        status = self.runCommand(command, cwd=abs_objdir, env=env,
                                 error_list=MakefileErrorList,
                                 halt_on_failure=True)
        command = "make package-tests"
        if package_type == 'multi':
            command += " AB_CD=multi"
        status = self.runCommand(command, cwd=abs_objdir, env=env,
                                 error_list=MakefileErrorList,
                                 halt_on_failure=True)

# __main__ {{{1
if __name__ == '__main__':
    multiLocaleRepack = MultiLocaleRepack()
    multiLocaleRepack.run()
