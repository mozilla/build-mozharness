#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import os
import sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.gaia_test import GaiaTest
from mozharness.mozilla.testing.unittest import TestSummaryOutputParserHelper


class GaiaUnitTest(GaiaTest):
    def __init__(self, require_config_file=False):
      GaiaTest.__init__(self, require_config_file)

    def run_tests(self):
        """
        Run the unit test suite.
        """
        dirs = self.query_abs_dirs()

        # make the gaia profile
        self.make_gaia(dirs['abs_gaia_dir'],
                       self.config.get('xre_path'),
                       debug=True)

        # build the testrunner command arguments
        python = self.query_python_path('python')
        cmd = [python, '-u', os.path.join(dirs['abs_runner_dir'],
                                          'gaia_unit_test',
                                          'main.py')]
        cmd.extend(self._build_arg('--binary', os.path.join(dirs['abs_work_dir'],
                                                            'b2g', 'b2g-bin')))
        cmd.extend(self._build_arg('--profile', os.path.join(dirs['abs_gaia_dir'],
                                                             'profile-debug')))

        output_parser = TestSummaryOutputParserHelper(config=self.config,
                                                      log_obj=self.log_obj,
                                                      error_list=self.error_list)
        code = self.run_command(cmd,
                                output_parser=output_parser)

        output_parser.print_summary('gaia-unit-tests')
        self.publish(code)

if __name__ == '__main__':
    gaia_unit_test = GaiaUnitTest()
    gaia_unit_test.run_and_exit()
