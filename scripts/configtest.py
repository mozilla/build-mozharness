#!/usr/bin/env python
"""configtest.py

Verify the .json and .py files in the configs/ directory are well-formed.

Further tests to verify validity would be desirable.
"""

import os
import sys
try:
    import json
except:
    import simplejson as json

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
        self.test_files = []
        BaseScript.__init__(self, config_options=self.config_options,
                            all_actions=['list-config-files',
                                         'test-json-configs',
                                         'test-python-configs',
                                         ],
                            require_config_file=require_config_file)

    def run(self):
        pass
#        self.dump_config()
#        self.list_config_files()
#        self.test_json_configs()
#        self.test_python_configs()
#        self.summary()

    def list_config_files(self):
        if 'list-config-files' not in self.actions:
            self.actionMessage("Skipping list config files step.")
            return
        self.actionMessage("Listing config files.")
        c = self.config

# __main__ {{{1
if __name__ == '__main__':
    config_test = ConfigTest()
    config_test.run()
