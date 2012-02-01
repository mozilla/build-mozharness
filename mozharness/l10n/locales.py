#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla.
#
# The Initial Developer of the Original Code is
# the Mozilla Foundation <http://www.mozilla.org/>.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Aki Sasaki <aki@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
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
        """ Mixins generally don't have an __init__.
        This breaks super().__init__() for children.
        However, this is needed to override the query_abs_dirs()
        """
        self.abs_dirs = None
        self.locales = None

    def query_locales(self):
        if self.locales is not None:
            return self.locales
        c = self.config
        locales = c.get("locales", None)
        ignore_locales = c.get("ignore_locales", [])
        additional_locales = c.get("additional_locales", [])

        if locales is None:
            locales = []
            if 'locales_file' in c:
                # Best way to get abs/relative path to this?
                locales_file = os.path.join(c['base_work_dir'], c['work_dir'],
                                            c['locales_file'])
                locales = self.parse_locales_file(locales_file)
            else:
                self.fatal("No way to determine locales!")
        for locale in ignore_locales:
            if locale in locales:
                self.debug("Ignoring locale %s." % locale)
                locales.remove(locale)
        for locale in additional_locales:
            if locale not in locales:
                self.debug("Adding locale %s." % locale)
                locales.append(locale)
        if locales is not None:
            self.locales = locales

        return self.locales

    def parse_locales_file(self, locales_file):
        locales = []
        c = self.config
        platform = c.get("locales_platform", None)

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
        return locales

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
        self.mkdir_p(dirs['abs_merge_dir'])
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
        # TODO prettify this up later
        if 'l10n_dir' in c:
            dirs['abs_l10n_dir'] = os.path.join(dirs['abs_work_dir'],
                                                c['l10n_dir'])
        if 'mozilla_dir' in c:
            dirs['abs_mozilla_dir'] = os.path.join(dirs['abs_work_dir'],
                                                   c['mozilla_dir'])
            dirs['abs_locales_src_dir'] = os.path.join(dirs['abs_mozilla_dir'],
                                                       c['locales_dir'])
            dirs['abs_l10n_dir'] = os.path.join(dirs['abs_work_dir'],
                                                c['l10n_dir'])
        if 'objdir' in c:
            dirs['abs_objdir'] = os.path.join(dirs['abs_mozilla_dir'],
                                              c['objdir'])
            dirs['abs_merge_dir'] = os.path.join(dirs['abs_objdir'],
                                                 'merged')
            dirs['abs_locales_dir'] = os.path.join(dirs['abs_objdir'],
                                                   c['locales_dir'])
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
