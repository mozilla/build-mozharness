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

from mozharness.mozilla.testing.gaia_test import GaiaTest
from mozharness.mozilla.testing.unittest import TestSummaryOutputParserHelper


class GaiaIntegrationTest(GaiaTest):

    def __init__(self, require_config_file=False):
      GaiaTest.__init__(self, require_config_file)

    def run_tests(self):
        """
        Run the integration test suite.
        """
        dirs = self.query_abs_dirs()

        self.node_setup()

        output_parser = TestSummaryOutputParserHelper(
          config=self.config, log_obj=self.log_obj, error_list=self.error_list)

        # Bug 1046694 - add environment variables which govern test chunking
        env = {}
        if self.config.get('this_chunk') and self.config.get('total_chunks'):
            env["PART"] = self.config.get('this_chunk')
            env["NBPARTS"] = self.config.get('total_chunks')
        env = self.query_env(partial_env=env)

        # `make test-integration \
        #      MOCHA_REPORTER=mocha-tbpl-reporter \
        #      NPM_REGISTRY=http://npm-mirror.pub.build.mozilla.org`
        cmd = [
            'make',
            'test-integration',
            'NPM_REGISTRY=' + self.config.get('npm_registry'),
            'REPORTER=mocha-tbpl-reporter',
            'TEST_MANIFEST=./shared/test/integration/tbpl-manifest.json'
        ]

        # for Mulet
        if 'firefox' in self.binary_path:
            cmd += ['RUNTIME=%s' % self.binary_path]

        code = self.run_command(cmd, cwd=dirs['abs_gaia_dir'], env=env,
           output_parser=output_parser,
           output_timeout=330)

        output_parser.print_summary('gaia-integration-tests')
        self.publish(code, passed=output_parser.passed, failed=output_parser.failed)

if __name__ == '__main__':
    gaia_integration_test = GaiaIntegrationTest()
    gaia_integration_test.run_and_exit()
