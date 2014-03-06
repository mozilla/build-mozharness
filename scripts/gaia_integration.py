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
from mozharness.base.log import ERROR
from mozharness.base.errors import BaseErrorList
from mozharness.mozilla.testing.unittest import TestSummaryOutputParserHelper


class GaiaIntegrationTest(GaiaTest):

    npm_error_list = BaseErrorList + [
        {'substr': r'''npm ERR! Error:''', 'level': ERROR}
    ]

    def __init__(self, require_config_file=False):
      GaiaTest.__init__(self, require_config_file)

    def run_tests(self):
        """
        Run the integration test suite.
        """
        dirs = self.query_abs_dirs()

        # Copy the b2g desktop we built to the gaia directory so that it
        # gets used by the marionette-js-runner.
        self.copytree(
            os.path.join(os.path.dirname(self.binary)),
            os.path.join(dirs['abs_gaia_dir'], 'b2g'),
            overwrite='clobber'
        )

        self.run_command(['npm', 'cache', 'clean'])

        # run 'make node_modules' first, so we can separately handle
        # errors that occur here
        cmd = ['make', 'node_modules']
        kwargs = {
            'cwd': dirs['abs_gaia_dir'],
            'output_timeout': 300,
            'error_list': self.npm_error_list
        }
        code = self.retry(self.run_command, attempts=3, good_statuses=(0,),
                          args=[cmd], kwargs=kwargs)
        if code:
            # Dump npm-debug.log, if it exists
            npm_debug = os.path.join(dirs['abs_gaia_dir'], 'npm-debug.log')
            if os.access(npm_debug, os.F_OK):
                self.info('dumping npm-debug.log')
                self.run_command(['cat', npm_debug])
            else:
                self.info('npm-debug.log doesn\'t exist, not dumping')
            self.fatal('Errors during \'npm install\'', exit_code=code)

        output_parser = TestSummaryOutputParserHelper(
          config=self.config, log_obj=self.log_obj, error_list=self.error_list)

        # `make test-integration \
        #      MOCHA_REPORTER=mocha-tbpl-reporter \
        #      NPM_REGISTRY=http://npm-mirror.pub.build.mozilla.org`
        code = self.run_command([
            'make',
            'test-integration',
            'NPM_REGISTRY=' + self.config.get('npm_registry'),
            'REPORTER=mocha-tbpl-reporter',
            'TEST_MANIFEST=./shared/test/integration/tbpl-manifest.json'
        ], cwd=dirs['abs_gaia_dir'],
           output_parser=output_parser,
           output_timeout=330)

        output_parser.print_summary('gaia-integration-tests')
        self.publish(code)

if __name__ == '__main__':
    gaia_integration_test = GaiaIntegrationTest()
    gaia_integration_test.run_and_exit()
