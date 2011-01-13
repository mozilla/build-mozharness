#!/usr/bin/env python
"""configtest.py

Verify the .json and .py files in the configs/ directory are well-formed.

Further tests to verify validity would be desirable.
"""

import os
import pprint
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
        self.config_files = []
        BaseScript.__init__(self, config_options=self.config_options,
                            all_actions=['list-config-files',
                                         'test-json-configs',
                                         'test-python-configs',
                                         ],
                            default_actions=['test-json-configs',
                                             'test-python-configs'],
                            require_config_file=require_config_file)

    def run(self):
        self.dump_config()
        self.list_config_files()
        self.test_json_configs()
        self.test_python_configs()
        self.summary()

    def dump_config(self):
        self.action_message("Dumping config")
        self.info("Note that some of these are not used.")
        self.info("Running config:")
        for key in sorted(self.config.keys()):
            self.info(" %s = %s" % (key, self.config[key]))
        self.info("Actions:")
        for action in self.actions:
            self.info(" %s" % action)

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
                    config_files.append(os.path.join(root, name))
        self.config_files = config_files
        return self.config_files

    def list_config_files(self):
        if 'list-config-files' not in self.actions:
            self.action_message("Skipping list config files step.")
            return
        self.action_message("Listing config files.")
        config_files = self.query_config_files()
        for config_file in config_files:
            self.info(config_file)

    def test_json_configs(self):
        """ Currently only "is this well-formed json?"

        """
        if 'test-json-configs' not in self.actions:
            self.action_message("Skipping test json configs step.")
            return
        self.action_message("Testing json config files.")
        config_files = self.query_config_files()
        filecount = [0, 0]
        for config_file in config_files:
            if config_file.endswith(".json"):
                filecount[0] += 1
                self.info("Testing %s." % config_file)
                fh = open(config_file)
                try:
                    json.load(fh)
                except:
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
        if 'test-python-configs' not in self.actions:
            self.action_message("Skipping test python configs step.")
            return
        self.action_message("Testing python config files.")
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
