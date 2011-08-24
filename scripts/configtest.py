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
"""configtest.py

Verify the .json and .py files in the configs/ directory are well-formed.

Further tests to verify validity would be desirable.
"""

import os
import pprint
import sys
try:
    import simplejson as json
except ImportError:
    import json

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.script import BaseScript

# ConfigTest {{{1
class ConfigTest(BaseScript):
    config_options = [[
     ["--test-file",],
     {"action": "extend",
      "dest": "test_files",
      "help": "Specify which config files to test"
     }
    ]]

    def __init__(self, require_config_file=False):
        self.config_files = []
        BaseScript.__init__(self, config_options=self.config_options,
                            all_actions=['list-config-files',
                                         'test-json-configs',
                                         'test-python-configs',
                                         ],
                            default_actions=['test-json-configs',
                                             'test-python-configs'],
                            require_config_file=require_config_file)

    def query_config_files(self):
        if self.config_files:
            return self.config_files
        c = self.config
        if 'test_files' in c:
            self.config_files = c['test_files']
            return self.config_files
        self.debug("No --test-file(s) specified; defaulting to crawling the configs/ directory.")
        config_files = []
        for root, dirs, files in os.walk(os.path.join(sys.path[0], "..",
                                                      "configs")):
            for name in files:
                # Hardcode =P
                if name.endswith(".json") or name.endswith(".py"):
                    if not name.startswith("test_malformed"):
                        config_files.append(os.path.join(root, name))
        self.config_files = config_files
        return self.config_files

    def list_config_files(self):
        config_files = self.query_config_files()
        for config_file in config_files:
            self.info(config_file)

    def test_json_configs(self):
        """ Currently only "is this well-formed json?"

        """
        config_files = self.query_config_files()
        filecount = [0, 0]
        for config_file in config_files:
            if config_file.endswith(".json"):
                filecount[0] += 1
                self.info("Testing %s." % config_file)
                fh = open(config_file)
                try:
                    json.load(fh)
                except ValueError:
                    self.add_summary("%s is invalid json." % config_file,
                                     level="error")
                    self.error(pprint.pformat(sys.exc_info()[1]))
                else:
                    self.info("Good.")
                    filecount[1] += 1
        if filecount[0]:
            self.add_summary("%d of %d json config files were good." %
                             (filecount[1], filecount[0]))
        else:
            self.add_summary("No json config files to test.")

    def test_python_configs(self):
        """Currently only "will this give me a config dictionary?"

        """
        config_files = self.query_config_files()
        filecount = [0, 0]
        for config_file in config_files:
            if config_file.endswith(".py"):
                filecount[0] += 1
                self.info("Testing %s." % config_file)
                global_dict = {}
                local_dict = {}
                try:
                    execfile(config_file, global_dict, local_dict)
                except:
                    self.add_summary("%s is invalid python." % config_file,
                                     level="error")
                    self.error(pprint.pformat(sys.exc_info()[1]))
                else:
                    if 'config' in local_dict and isinstance(local_dict['config'], dict):
                        self.info("Good.")
                        filecount[1] += 1
                    else:
                        self.add_summary("%s is valid python, but doesn't create a config dictionary." %
                                         config_file, level="error")
        if filecount[0]:
            self.add_summary("%d of %d python config files were good." %
                             (filecount[1], filecount[0]))
        else:
            self.add_summary("No python config files to test.")

# __main__ {{{1
if __name__ == '__main__':
    config_test = ConfigTest()
    config_test.run()
