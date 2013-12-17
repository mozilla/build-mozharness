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


class GaiaIntegrationTest(GaiaTest):
    def __init__(self, require_config_file=False):
      GaiaTest.__init__(self, require_config_file)

    def run_tests(self):
        """
        Run the integration test suite.
        """
        dirs = self.query_abs_dirs()

        output_parser = TestSummaryOutputParserHelper(
          config=self.config, log_obj=self.log_obj, error_list=self.error_list)

        # Copy the b2g desktop we built to the gaia directory so that it
        # gets used by the marionette-js-runner.
        self.copytree(
            os.path.join(dirs['abs_work_dir'], 'b2g'),
            os.path.join(dirs['abs_gaia_dir'], 'b2g'),
            overwrite='clobber'
        )

        self.info('Bug 935576 - Add more logging to debug failing tests')
        cmd_to_result = {}
        cmd_to_result['find'] = self.run_command(
            self.query_exe('find', return_type='list') + ['.'],
            cwd=dirs['abs_gaia_dir']
        )
        cmd_to_result['ls'] = self.run_command(
            self.query_exe('ls', return_type='string'),
            cwd=dirs['abs_gaia_dir']
        )
        cmd_to_result['printenv'] = self.run_command(
            self.query_exe('printenv', return_type='string'),
            cwd=dirs['abs_gaia_dir']
        )
        cmd_to_result['pwd'] = self.run_command(
            self.query_exe('pwd', return_type='string'),
            cwd=dirs['abs_gaia_dir']
        )
        cmd_to_result['whoami'] = self.run_command(
            self.query_exe('whoami', return_type='string'),
            cwd=dirs['abs_gaia_dir']
        )
        for cmd, result in cmd_to_result.iteritems():
            self.info('=================')
            self.info('%s output' % cmd)
            self.info('=================')
            self.info(result)

        # `make test-integration \
        #      MOCHA_REPORTER=mocha-tbpl-reporter \
        #      NPM_REGISTRY=http://npm-mirror.pub.build.mozilla.org`
        make = self.query_exe('make', return_type='list')
        make = make + ['test-integration']
        code = self.run_command(make, cwd=dirs['abs_gaia_dir'], env={
          'NPM_REGISTRY': self.config.get('npm_registry'),
          'REPORTER': 'mocha-tbpl-reporter',
          'USE_LOCAL_XULRUNNER_SDK': '1',
          'XULRUNNER_DIRECTORY': self.config.get('xre_dir')
        }, output_parser=output_parser)

        output_parser.print_summary('gaia-integration-tests')
        self.publish(code)

if __name__ == '__main__':
    gaia_integration_test = GaiaIntegrationTest()
    gaia_integration_test.run_and_exit()
