#!/usr/bin/env python
"""Localization.
"""

import os
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.config import parse_config_file

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

# __main__ {{{1

if __name__ == '__main__':
    pass
