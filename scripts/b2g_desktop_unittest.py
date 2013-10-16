#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import os
import re
import sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import BaseErrorList
from mozharness.base.log import ERROR
from mozharness.base.script import (
    BaseScript,
    PreScriptAction,
)
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options
from mozharness.mozilla.testing.unittest import DesktopUnittestOutputParser
from mozharness.mozilla.tooltool import TooltoolMixin


class B2GDesktopTest(TestingMixin, TooltoolMixin, MercurialScript, BaseScript):
    test_suites = ('mochitest',)
    config_options = [
        [["--type"],
        {"action": "store",
         "dest": "test_type",
         "default": "browser",
         "help": "The type of tests to run",
        }],
        [["--test-manifest"],
        {"action": "store",
         "dest": "test_manifest",
         "default": None,
         "help": "Path to test manifest to run",
        }],
        [["--test-suite"],
        {"action": "store",
         "dest": "test_suite",
         "type": "choice",
         "choices": test_suites,
         "help": "Which test suite to run",
        }],
        [["--total-chunks"],
        {"action": "store",
         "dest": "total_chunks",
         "help": "Number of total chunks",
        }],
        [["--this-chunk"],
        {"action": "store",
         "dest": "this_chunk",
         "help": "Number of this chunk",
        }]] + copy.deepcopy(testing_config_options)

    error_list = [
        {'substr': 'FAILED (errors=', 'level': ERROR},
        {'substr': r'''Could not successfully complete transport of message to Gecko, socket closed''', 'level': ERROR},
        {'substr': 'Timeout waiting for marionette on port', 'level': ERROR},
        {'regex': re.compile(r'''(Timeout|NoSuchAttribute|Javascript|NoSuchElement|XPathLookup|NoSuchWindow|StaleElement|ScriptTimeout|ElementNotVisible|NoSuchFrame|InvalidElementState|NoAlertPresent|InvalidCookieDomain|UnableToSetCookie|InvalidSelector|MoveTargetOutOfBounds)Exception'''), 'level': ERROR},
    ]

    def __init__(self, require_config_file=False):
        super(B2GDesktopTest, self).__init__(
            config_options=self.config_options,
            all_actions=['clobber',
                         'read-buildbot-config',
                         'download-and-extract',
                         'create-virtualenv',
                         'install',
                         'run-tests'],
            default_actions=['clobber',
                             'download-and-extract',
                             'create-virtualenv',
                             'install',
                             'run-tests'],
            require_config_file=require_config_file,
            config={
                'require_test_zip': True,
            }
        )

        # these are necessary since self.config is read only
        c = self.config
        self.installer_url = c.get('installer_url')
        self.installer_path = c.get('installer_path')
        self.test_url = c.get('test_url')
        self.test_manifest = c.get('test_manifest')

    # TODO detect required config items and fail if not set

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(B2GDesktopTest, self).query_abs_dirs()
        dirs = {}
        dirs['abs_tests_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'tests')
        for d in ('mochitest', 'config', 'certs'):
            dirs['abs_%s_dir' % d] = os.path.join(
                    dirs['abs_tests_dir'], d)

        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def download_and_extract(self):
        super(B2GDesktopTest, self).download_and_extract()

        if self.config.get('download_minidump_stackwalk'):
            self.install_minidump_stackwalk()

    @PreScriptAction('create-virtualenv')
    def _pre_create_virtualenv(self, action):
        if self.tree_config.get('use_puppetagain_packages'):
            requirements = [os.path.join('tests', 'b2g',
                'b2g-unittest-requirements.txt')]

            self.register_virtualenv_module('mozinstall',
                requirements=requirements)
            self.register_virtualenv_module('marionette',
                url=os.path.join('tests', 'marionette'), requirements=requirements)
            return

        dirs = self.query_abs_dirs()
        requirements = os.path.join(dirs['abs_config_dir'],
                                    'marionette_requirements.txt')
        self.register_virtualenv_module(requirements=[requirements],
                                        two_pass=True)

    def _query_abs_base_cmd(self, suite):
        dirs = self.query_abs_dirs()
        cmd = [self.query_python_path('python')]
        cmd.append(self.config['run_file_names'][suite])

        str_format_values = {
            'application': self.binary_path,
            'test_manifest': self.test_manifest,
            'symbols_path': self.symbols_path,
            'gaia_profile': self.gaia_profile,
            'utility_path': os.path.join(dirs['abs_tests_dir'], 'bin'),
            'total_chunks': self.config.get('total_chunks'),
            'this_chunk': self.config.get('this_chunk'),
            'cert_path': dirs['abs_certs_dir'],
        }

        name = '%s_options' % suite
        options = self.tree_config.get(name, self.config.get(name))
        if options:
            for option in options:
                option = option % str_format_values
                if not option.endswith('None'):
                    cmd.append(option)
        return cmd

    def preflight_run_tests(self):
        super(B2GDesktopTest, self).preflight_run_tests()
        suite = self.config['test_suite']
        # set default test manifest by suite if none specified
        if not self.test_manifest:
            if suite == 'mochitest':
                self.test_manifest = 'b2g-desktop.json'

        # set the gaia_profile
        self.gaia_profile = os.path.join(os.path.dirname(self.binary_path),
                                         'gaia', 'profile')

    def run_tests(self):
        """
        Run the tests
        """
        dirs = self.query_abs_dirs()

        error_list = self.error_list
        error_list.extend(BaseErrorList)

        suite = self.config['test_suite']
        if suite not in self.test_suites:
            self.fatal("Don't know how to run --test-suite '%s'!" % suite)

        cmd = self._query_abs_base_cmd(suite)
        cwd = dirs['abs_%s_dir' % suite]

        # TODO we probably have to move some of the code in
        # scripts/desktop_unittest.py and scripts/marionette.py to
        # mozharness.mozilla.testing.unittest so we can share it.
        # In the short term, I'm ok with some duplication of code if it
        # expedites things; please file bugs to merge if that happens.

        suite_name = [x for x in self.test_suites if x in self.config['test_suite']][0]
        if self.config.get('this_chunk'):
            suite = '%s-%s' % (suite_name, self.config['this_chunk'])
        else:
            suite = suite_name

        # bug 773703
        success_codes = None
        if suite_name == 'xpcshell':
            success_codes = [0, 1]

        env = {}
        if self.query_minidump_stackwalk():
            env['MINIDUMP_STACKWALK'] = self.minidump_stackwalk_path
        env = self.query_env(partial_env=env)

        parser = DesktopUnittestOutputParser(suite_category=suite_name,
                                                config=self.config,
                                                log_obj=self.log_obj,
                                                error_list=error_list)
        return_code = self.run_command(cmd, cwd=cwd, env=env,
                                       output_timeout=1000,
                                       output_parser=parser,
                                       success_codes=success_codes)

        tbpl_status, log_level = parser.evaluate_parser(return_code)
        parser.append_tinderboxprint_line(suite_name)

        self.buildbot_status(tbpl_status, level=log_level)
        self.log("The %s suite: %s ran with return status: %s" %
                 (suite_name, suite, tbpl_status), level=log_level)

if __name__ == '__main__':
    desktopTest = B2GDesktopTest()
    desktopTest.run_and_exit()
