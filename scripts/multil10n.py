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
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import SSHErrorList, PythonErrorList, MakefileErrorList
from mozharness.base.script import MercurialScript
from mozharness.l10n import LocalesMixin



# MultiLocaleBuild {{{1
class MultiLocaleBuild(LocalesMixin, MercurialScript):
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
        LocalesMixin.__init__(self)
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
#                                 default_actions=['pull-locale-source',
#                                                  'add-locales',
#                                                  'package-multi'],
                                 require_config_file=require_config_file)

    def run(self):
        self.clobber()
        self.pull()
        self.build()
        self.package(package_type='en-US')
#        self.upload(package_type='en-US')
        self.add_locales()
        self.package(package_type='multi')
#        self.upload(package_type='multi')

    def query_abs_dirs(self):
        if hasattr(self, "abs_dirs"):
            return self.abs_dirs
        c = self.config
        dirs = {}
        dirs['abs_work_dir'] = os.path.join(c['base_work_dir'],
                                            c['work_dir'])
        dirs['abs_l10n_dir'] = os.path.join(dirs['abs_work_dir'],
                                            c['l10n_dir'])
        dirs['abs_mozilla_dir'] = os.path.join(dirs['abs_work_dir'],
                                               c['mozilla_dir'])
        dirs['abs_objdir'] = os.path.join(dirs['abs_mozilla_dir'],
                                          c['objdir'])
        dirs['abs_merge_dir'] = os.path.join(dirs['abs_objdir'],
                                             'merged')
        dirs['abs_locales_dir'] = os.path.join(dirs['abs_objdir'],
                                               c['locales_dir'])
        dirs['abs_locales_src_dir'] = os.path.join(dirs['abs_mozilla_dir'],
                                                   c['locales_dir'])
        dirs['abs_l10n_dir'] = os.path.join(dirs['abs_work_dir'],
                                            c['l10n_dir'])
        dirs['abs_compare_locales_dir'] = os.path.join(dirs['abs_work_dir'],
                                                       'compare-locales')
        self.abs_dirs = dirs
        return self.abs_dirs

    def clobber(self):
        if 'clobber' not in self.actions:
            self.action_message("Skipping clobber step.")
            return
        self.action_message("Clobbering.")
        c = self.config
        if c['work_dir'] != '.':
            path = os.path.join(c['base_work_dir'], c['work_dir'])
            if os.path.exists(path):
                self.rmtree(path, error_level='fatal')
        # TODO what to do otherwise?

    def pull(self):
        c = self.config
        dirs = self.query_abs_dirs()
        if 'pull-build-source' not in self.actions:
            self.action_message("Skipping pull build source step.")
        else:
            self.action_message("Pulling.")
            self.scm_checkout_repos(c['repos'])

        if 'pull-locale-source' not in self.actions:
            self.action_message("Skipping pull locale source step.")
        else:
            self.action_message("Pulling locale source.")
            self.mkdir_p(dirs['abs_l10n_dir'])
            locales = self.query_locales()
            locale_repos = []
            for locale in locales:
                locale_dict = {
                    
                }
                tag = c['hg_l10n_tag']
                if hasattr(self, 'locale_dict'):
                    tag = self.locale_dict[locale]
                locale_repos.append({
                    'repo': "%s/%s" % (c['hg_l10n_base'], locale),
                    'tag': tag
                })
            self.scm_checkout_repos(repo_list=locale_repos,
                                    parent_dir=dirs['abs_l10n_dir'])

    def build(self):
        if 'build' not in self.actions:
            self.action_message("Skipping build step.")
            return
        self.action_message("Building.")
        c = self.config
        dirs = self.query_abs_dirs()
        self.copyfile(os.path.join(dirs['abs_work_dir'], c['mozconfig']),
                      os.path.join(dirs['abs_mozilla_dir'], 'mozconfig'),
                      error_level='fatal')
        command = "make -f client.mk build"
        # TODO a better way to do envs
        env = self.generate_env(partial_env=c['java_env'],
                                replace_dict={'PATH': os.environ['PATH']})
        self.run_command(command, cwd=dirs['abs_mozilla_dir'], env=env,
                         error_list=MakefileErrorList,
                         halt_on_failure=True)

    def add_locales(self):
        if 'add-locales' not in self.actions:
            self.action_message("Skipping add-locales step.")
            return
        self.action_message("Adding locales to the apk.")
        c = self.config
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        compare_locales_script = os.path.join(dirs['abs_compare_locales_dir'],
                                              'scripts', 'compare-locales')
        env = self.generate_env(partial_env={'PYTHONPATH':
                                os.path.join(dirs['abs_compare_locales_dir'],
                                             'lib')})
        compare_locales_error_list = list(PythonErrorList)

        for locale in locales:
            self.rmtree(dirs['abs_merge_dir'])
            command = "python %s -m %s l10n.ini %s %s" % (compare_locales_script,
                      dirs['abs_merge_dir'], dirs['abs_l10n_dir'], locale)
            self.run_command(command, error_list=compare_locales_error_list,
                             cwd=dirs['abs_locales_src_dir'], env=env,
                             halt_on_failure=True)
            command = 'make chrome-%s L10NBASEDIR=%s' % (locale, dirs['abs_l10n_dir'])
            if c['merge_locales']:
                command += " LOCALE_MERGEDIR=%s" % dirs['abs_merge_dir']
                self.run_command(command, cwd=dirs['abs_locales_dir'],
                                 error_list=MakefileErrorList,
                                 halt_on_failure=True)

    def package(self, package_type='en-US'):
        if 'package-%s' % package_type not in self.actions:
            self.action_message("Skipping package-%s." % package_type)
            return
        self.action_message("Packaging %s." % package_type)
        c = self.config
        dirs = self.query_abs_dirs()

        command = "make package"
        # only a little ugly?
        # TODO c['package_env'] that automatically replaces %(PATH),
        # %(abs_work_dir)
        partial_env = c['java_env'].copy()
        env = self.generate_env(partial_env=c['java_env'],
                                replace_dict={'PATH': os.environ['PATH']})
        if package_type == 'multi':
            command += " AB_CD=multi"
            partial_env['MOZ_CHROME_MULTILOCALE'] = "en-US " + \
                                                   ' '.join(self.query_locales())
            self.info("MOZ_CHROME_MULTILOCALE is %s" % partial_env['MOZ_CHROME_MULTILOCALE'])
        if 'jarsigner' in c:
            # hm, this is pretty mozpass.py specific
            partial_env['JARSIGNER'] = os.path.join(dirs['abs_work_dir'],
                                                    c['jarsigner'])
        status = self.run_command(command, cwd=dirs['abs_objdir'], env=env,
                                  error_list=MakefileErrorList,
                                  halt_on_failure=True)
        command = "make package-tests"
        if package_type == 'multi':
            command += " AB_CD=multi"
        status = self.run_command(command, cwd=dirs['abs_objdir'], env=env,
                                  error_list=MakefileErrorList,
                                  halt_on_failure=True)

# __main__ {{{1
if __name__ == '__main__':
    multi_locale_build = MultiLocaleBuild()
    multi_locale_build.run()
