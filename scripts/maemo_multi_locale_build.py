#!/usr/bin/env python
"""maemo_multi_locale_build.py

Override MultiLocaleBuild with Maemo- and scratchbox-isms.
"""

import hashlib
import os
import re
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import MakefileErrorList, PythonErrorList
from mozharness.l10n.multi_locale_build import MultiLocaleBuild



# MaemoMultiLocaleBuild {{{1
class MaemoMultiLocaleBuild(MultiLocaleBuild):
    config_options = MultiLocaleBuild.config_options + [[
     ["--deb-name",],
     {"action": "store",
      "dest": "deb_name",
      "type": "string",
      "help": "Specify the name of the deb",
     }
    ],[
     ["--sbox-target",],
     {"action": "store",
      "dest": "sbox_target",
      "type": "choice",
      "choices": ["FREMANTLE_ARMEL", "CHINOOK-ARMEL-2007"],
      "default": "FREMANTLE_ARMEL",
      "help": "Specify the scratchbox target"
     }
    ],[
     ["--sbox-home",],
     {"action": "store",
      "dest": "sbox_home",
      "type": "string",
      "default": "/scratchbox/users/cltbld/home/cltbld/",
      "help": "Specify the scratchbox user home directory"
     }
    ],[
     ["--sbox-root",],     {"action": "store",
      "dest": "sbox_root",
      "type": "string",
      "default": "/scratchbox/users/cltbld",
      "help": "Specify the scratchbox user home directory"
     }
    ],[
     ["--sbox_path",],
     {"action": "store",
      "dest": "sbox_path",
      "type": "string",
      "default": "/scratchbox/moz_scratchbox",
      "help": "Specify the scratchbox executable"
     }
    ]]

    def __init__(self, require_config_file=True, **kwargs):
        super(MaemoMultiLocaleBuild, self).__init__(
         require_config_file=require_config_file,
         **kwargs
        )
        self.deb_name = None
        self.deb_package_version = None

    def set_sbox_target(self):
        c = self.config
        self.info("Checking scratchbox target.")
        sbox_target = self.get_output_from_command("%s -p sb-conf current" %
                                                   c['sbox_path']).split('\n')[-1]
        if sbox_target != c['sbox_target']:
            self.info("%s is not %s.  Setting scratchbox target." % (
                      sbox_target, c['sbox_target']))
            self.run_command("%s -p sb-conf select %s" % (c['sbox_path'],
                                                          c['sbox_target']),
                             halt_on_failure=True)
        else:
            self.debug("Scratchbox target is already set correctly.")

    def preflight_build(self):
        self.set_sbox_target()

    def _preflight_package(self):
        dirs = self.query_abs_dirs()
        self.set_sbox_target()
        self.run_command("rm -fv dist/*.tar.* mobile/*.deb dist/deb_name.txt dist/*.zip",
                         cwd=dirs['abs_objdir'], halt_on_failure=False)

    def preflight_package_en_US(self):
        self._preflight_package()

    def preflight_package_multi(self):
        self._preflight_package()
        dirs = self.query_abs_dirs()
        self.run_command("rm -rfv dist/fennec*", cwd=dirs['abs_objdir'])

    def add_locales(self):
        c = self.config
        dirs = self.query_abs_dirs()
        locales = self.query_locales()

        for locale in locales:
            self.run_compare_locales(locale, halt_on_failure=True)
            # TODO Not proud of this hardcode -- how to fix?
            command = 'make chrome-%s L10NBASEDIR=%s' % (locale,
                      dirs['abs_l10n_dir'].replace(c['sbox_root'], ""))
            if c['merge_locales']:
                command += " LOCALE_MERGEDIR=%s" % dirs['abs_merge_dir'].replace(c['sbox_root'], "")
                self._process_command(command=command,
                                      cwd=dirs['abs_locales_dir'],
                                      error_list=MakefileErrorList,
                                      halt_on_failure=True)

    def additional_packaging(self, package_type='en-US', env=None):
        dirs = self.query_abs_dirs()
        command = "make deb"
        if package_type == 'multi':
            command += " AB_CD=multi"
        self._process_command(command=command, cwd=dirs['abs_objdir'],
                              env=env, error_list=MakefileErrorList,
                              halt_on_failure=True)
        command = "make package-tests PYTHON=python2.5"
        if package_type == 'multi':
            command += " AB_CD=multi"
        self._process_command(command=command, cwd=dirs['abs_objdir'],
                              env=env, error_list=MakefileErrorList,
                              halt_on_failure=True)
        # TODO deal with buildsymbols

    def _process_command(self, **kwargs):
        c = self.config
        command = '%s ' % c['sbox_path']
        if 'return_type' not in kwargs or kwargs['return_type'] != 'output':
            command += '-p '
        if 'env' in kwargs and kwargs['env'] is not None:
            command += '-k '
        if 'cwd' in kwargs:
            command += '-d %s ' % kwargs['cwd'].replace(c['sbox_home'], '')
            del kwargs['cwd']
        kwargs['command'] = '%s "%s"' % (command, kwargs['command'].replace(c['sbox_root'], ''))
        if 'return_type' not in kwargs or kwargs['return_type'] != 'output':
            if 'error_list' in kwargs:
                kwargs['error_list'] = PythonErrorList + kwargs['error_list']
            else:
                kwargs['error_list'] = PythonErrorList
            return self.run_command(**kwargs)
        else:
            del(kwargs['return_type'])
            return self.get_output_from_command(**kwargs)

# __main__ {{{1
if __name__ == '__main__':
    maemo_multi_locale_build = MaemoMultiLocaleBuild()
    maemo_multi_locale_build.run()
