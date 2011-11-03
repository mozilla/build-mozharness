#!/usr/bin/env python
"""test_browser.py

clobber, download/extract, and then run a dummy runtests.py command (via echo)

TODO: we need to add dmg support to OSMixin.extract() to be able to handle real life unit tests.
"""

import os
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import PythonErrorList
from mozharness.base.log import DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, IGNORE
from mozharness.base.script import BaseScript

# TestBrowserExample {{{1
class TestBrowserExample(BaseScript):
    config_options = [[
     ["--browser-url"],
     {"action": "store",
      "dest": "browser_url",
      "default": "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/8.0b6-candidates/build1/linux-i686/en-US/firefox-8.0b6.tar.bz2",
      "help": "Specify the browser url"
     }
    ],[
     ["--test-url"],
     {"action": "store",
      "dest": "test_url",
      "default": "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/8.0b6-candidates/build1/linux-i686/en-US/firefox-8.0b6.tests.zip",
      "help": "Specify the test zip url"
     }
    ]]

    def __init__(self, require_config_file=False):
        super(TestBrowserExample, self).__init__(
         config_options=self.config_options,
         all_actions=['clobber',
                      'download-and-extract',
                      'run-tests',
                      ],
         # Since the default_actions are the same as all_actions, they
         # don't need to be defined. Defining anyway for clarity/ease of
         # editing.
         default_actions=['clobber',
                          'download-and-extract',
                          'run-tests',
                          ],
         require_config_file=require_config_file,
        )

    def clobber(self):
        dirs = self.query_abs_dirs()
        self.rmtree(dirs['abs_work_dir'])

    def download_and_extract(self):
        c = self.config
        dirs = self.query_abs_dirs()
        self.mkdir_p(dirs['abs_work_dir'])
        file_name = os.path.join(dirs['abs_work_dir'],
                                 self.get_filename_from_url(c['browser_url']))
        # download browser_url or die
        self.download_file(c['browser_url'], file_name=file_name,
                           error_level=FATAL)
        self.extract(file_name)

        file_name = os.path.join(dirs['abs_work_dir'],
                                 self.get_filename_from_url(c['test_url']))
        # download test_url or die
        self.download_file(c['test_url'], file_name=file_name,
                           error_level=FATAL)
        self.extract(file_name)

    def preflight_run_tests(self):
        """ If this, or any other preflight_ACTION method, is defined,
        it will run before the action.  postflight_ACTION methods will run
        after the action.

        You could doublecheck that all the tests and browser are there
        and you have enough diskspace or w/e other checks you want to put
        in.
        """
        pass

    def run_tests(self):
        dirs = self.query_abs_dirs()
        args = ["--generate", "--args", "--from", "--config"]
        test_error_list = [
         {'substr': r'''TEST-UNEXPECTED-FAIL''', 'level': ERROR,},
         {'substr': r'''TEST-UNEXPECTED-PASS''', 'level': ERROR,},
         {'substr': r'''TEST-EXPECTED-FAIL''', 'level': INFO,},
         {'substr': r'''TEST-UNEXPECTED-WARNING''', 'level': WARNING,},
        ] + PythonErrorList

        cmd = ["echo", "runtests.py"] + args
        status = self.run_command(cmd, error_list=test_error_list,
                                  cwd=os.path.join(dirs['abs_work_dir'],
                                                   'mochitest'))
        self.add_summary("%s exited with status %s." % (cmd, str(status)))

# __main__ {{{1
if __name__ == '__main__':
    test_browser_example = TestBrowserExample()
    test_browser_example.run()
