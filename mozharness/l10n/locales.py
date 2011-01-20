#!/usr/bin/env python
"""Localization.
"""

import os
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.config import parse_config_file
from mozharness.base.errors import PythonErrorList

# LocalesMixin {{{1

class LocalesMixin(object):
    def __init__(self, **kwargs):
        self.locales = None

    def query_locales(self):
        if self.locales:
            return self.locales
        c = self.config
        locales = c.get("locales", None)
        ignore_locales = c.get("ignore_locales", None)

        if not locales:
            locales = []
            if 'locales_file' in c:
                # Best way to get abs/relative path to this?
                locales_file = os.path.join(c['base_work_dir'], c['work_dir'],
                                            c['locales_file'])
                locales = self.parse_locales_file(locales_file)
            else:
                self.fatal("No way to determine locales!")

        return locales

    def parse_locales_file(self, locales_file):
        locales = []
        c = self.config
        platform = c.get("locales_platform", None)
        ignore_locales = c.get("ignore_locales", None)

        if locales_file.endswith('json'):
            locales_json = parse_config_file(locales_file)
            self.locale_dict = {}
            for locale in locales_json.keys():
                if platform and platform not in locales_json[locale]['platforms']:
                    continue
                locales.append(locale)
                self.locale_dict[locale] = locales_json[locale]['revision']
        else:
            fh = open(locales_file)
            locales = fh.read().split()
            fh.close()
        if ignore_locales:
            for locale in ignore_locales:
                if locale in locales:
                    self.debug("Ignoring locale %s." % locale)
                    locales.remove(locale)
        if locales:
            self.locales = locales
            return self.locales

    def run_compare_locales(self, locale, halt_on_failure=False):
        c = self.config
        dirs = self.query_abs_dirs()
        compare_locales_script = os.path.join(dirs['abs_compare_locales_dir'],
                                              'scripts', 'compare-locales')
        env = self.query_env(partial_env={'PYTHONPATH':
                             os.path.join(dirs['abs_compare_locales_dir'],
                                          'lib')})
        compare_locales_error_list = list(PythonErrorList)
        self.rmtree(dirs['abs_merge_dir'])
        command = "python %s -m %s l10n.ini %s %s" % (compare_locales_script,
                  dirs['abs_merge_dir'], dirs['abs_l10n_dir'], locale)
        status = self.run_command(command, error_list=compare_locales_error_list,
                                  cwd=dirs['abs_locales_src_dir'], env=env,
                                  halt_on_failure=halt_on_failure)
        return status

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(LocalesMixin, self).query_abs_dirs()
        c = self.config
        dirs = {}
        dirs['abs_work_dir'] = os.path.join(c['base_work_dir'],
                                            c['work_dir'])
        dirs['abs_l10n_dir'] = os.path.join(dirs['abs_work_dir'],                                            c['l10n_dir'])
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
        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

# __main__ {{{1

if __name__ == '__main__':
    pass
