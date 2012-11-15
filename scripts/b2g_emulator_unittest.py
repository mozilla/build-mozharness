#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import copy
import os
import re
import sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import BaseErrorList
from mozharness.base.log import ERROR
from mozharness.base.script import BaseScript
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options
from mozharness.mozilla.testing.unittest import DesktopUnittestOutputParser, EmulatorMixin
from mozharness.mozilla.tooltool import TooltoolMixin


class B2GEmulatorTest(TestingMixin, TooltoolMixin, EmulatorMixin, BaseScript):
    config_options = [
        [["--type"],
        {"action": "store",
         "dest": "test_type",
         "default": "browser",
         "help": "The type of tests to run",
        }],
        [["--emulator-url"],
        {"action": "store",
         "dest": "emulator_url",
         "default": None,
         "help": "URL to the emulator zip",
        }],
        [["--xpcshell-url"],
        {"action": "store",
         "dest": "xpcshell_url",
         "default": None,
         "help": "URL to the desktop xpcshell zip",
        }],
        [["--gecko-url"],
        {"action": "store",
         "dest": "gecko_url",
         "default": None,
         "help": "URL to the gecko build injected into the emulator",
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
         "choices": ('reftest', 'mochitest'),
         "help": "Which test suite to run",
        }],
        [["--adb-path"],
        {"action": "store",
         "dest": "adb_path",
         "default": None,
         "help": "Path to adb",
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

    mozbase_dir = os.path.join('tests', 'mozbase')
    virtualenv_modules = [
        { 'manifestparser': os.path.join(mozbase_dir, 'manifestdestiny') },
        { 'mozfile': os.path.join(mozbase_dir, 'mozfile') },
        { 'mozhttpd': os.path.join(mozbase_dir, 'mozhttpd') },
        { 'mozinfo': os.path.join(mozbase_dir, 'mozinfo') },
        { 'mozinstall': os.path.join(mozbase_dir, 'mozinstall') },
        { 'mozprofile': os.path.join(mozbase_dir, 'mozprofile') },
        { 'mozprocess': os.path.join(mozbase_dir, 'mozprocess') },
        { 'mozrunner': os.path.join(mozbase_dir, 'mozrunner') },
        { 'mozdevice': os.path.join(mozbase_dir, 'mozdevice') },
        { 'marionette': os.path.join('tests', 'marionette') },
    ]

    def __init__(self, require_config_file=False):
        super(B2GEmulatorTest, self).__init__(
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
                'virtualenv_modules': self.virtualenv_modules,
                'require_test_zip': True,
                'emulator': 'arm',
                # This is a special IP that has meaning to the emulator
                'remote_webserver': '10.0.2.2',
            }
        )

        # these are necessary since self.config is read only
        c = self.config
        self.adb_path = c.get('adb_path', self._query_adb())
        self.installer_url = c.get('installer_url')
        self.installer_path = c.get('installer_path')
        self.test_url = c.get('test_url')
        self.test_manifest = c.get('test_manifest')

    # TODO detect required config items and fail if not set

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(B2GEmulatorTest, self).query_abs_dirs()
        dirs = {}
        dirs['abs_test_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'tests')
        dirs['abs_xpcshell_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'xpcshell')
        dirs['abs_emulator_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'emulator')
        dirs['abs_b2g-distro_dir'] = os.path.join(
            dirs['abs_emulator_dir'], 'b2g-distro')
        dirs['abs_mochitest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'mochitest')
        dirs['abs_reftest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'reftest')
        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def _build_arg(self, option, value):
        """
        Build a command line argument
        """
        if not value:
            return []
        return [str(option), str(value)]

    def download_and_extract(self):
        super(B2GEmulatorTest, self).download_and_extract()
        dirs = self.query_abs_dirs()
        self.install_emulator()

        self.mkdir_p(dirs['abs_xpcshell_dir'])
        self._download_unzip(self.config['xpcshell_url'],
                             dirs['abs_xpcshell_dir'])

    def _build_mochitest_args(self):
        c = self.config
        dirs = self.query_abs_dirs()
        python = self.query_python_path('python')
        cmd = [
            python, os.path.join(dirs['abs_mochitest_dir'], 'runtestsb2g.py'),
            '--emulator', c['emulator'],
            '--console-level', 'INFO',
            '--b2gpath', dirs['abs_b2g-distro_dir'],
            '--remote-webserver', c['remote_webserver'],
        ]
        cmd.extend(self._build_arg('--total-chunks', c.get('total_chunks')))
        cmd.extend(self._build_arg('--this-chunk', c.get('this_chunk')))
        # self.binary_path gets set by super(B2GEmulatorTest, self).install()
        cmd.extend(self._build_arg('--gecko-path', os.path.dirname(self.binary_path)))
        cmd.extend([
            '--run-only-tests', self.test_manifest,
            '--xre-path', os.path.join(dirs['abs_xpcshell_dir'], 'bin'),
            '--adbpath', self.adb_path,
        ])
        return cmd

    def _build_reftest_args(self):
        c = self.config
        dirs = self.query_abs_dirs()
        python = self.query_python_path('python')
        cmd = [
            python, 'runreftestb2g.py',
            '--emulator', c['emulator'],
            '--emulator-res', '800x1000',
            '--ignore-window-size',
            '--b2gpath', dirs['abs_b2g-distro_dir'],
            '--remote-webserver', c['remote_webserver'],
        ]
        cmd.extend(self._build_arg('--total-chunks', c.get('total_chunks')))
        cmd.extend(self._build_arg('--this-chunk', c.get('this_chunk')))
        # self.binary_path gets set by super(B2GEmulatorTest, self).install()
        cmd.extend(self._build_arg('--gecko-path', os.path.dirname(self.binary_path)))
        cmd.extend([
            '--xre-path', os.path.join(dirs['abs_xpcshell_dir'], 'bin'),
            '--adbpath', self.adb_path,
        ])
        cmd.append(self.test_manifest)
        return cmd

    def _query_adb(self):
        return self.which('adb') or \
               os.getenv('ADB_PATH') or \
               os.path.join(self.query_abs_dirs()['abs_b2g-distro_dir'],
                            'out', 'host', 'linux-x86', 'bin', 'adb')

    def preflight_run_tests(self):
        super(B2GEmulatorTest, self).preflight_run_tests()
        c = self.config
        # set default test manifest by suite if none specified
        if not self.test_manifest:
            if c['test_suite'] == 'mochitest':
                self.test_manifest = 'b2g.json'
            elif c['test_suite'] == 'reftest':
                self.test_manifest = os.path.join('tests', 'layout',
                                                  'reftests', 'reftest.list')

        if not os.path.isfile(self.adb_path):
            self.fatal("The adb binary '%s' is not a valid file!" % self.adb_path)

    def run_tests(self):
        """
        Run the tests
        """
        dirs = self.query_abs_dirs()

        error_list = self.error_list
        error_list.extend(BaseErrorList)

        if self.config['test_suite'] == 'mochitest':
            cmd = self._build_mochitest_args()
            cwd = dirs['abs_mochitest_dir']
        elif self.config['test_suite'] == 'reftest':
            cmd = self._build_reftest_args()
            cwd = dirs['abs_reftest_dir']
        else:
            self.fatal("Don't know how to run --test-suite '%s'!" % self.config['test_suite'])
        # TODO we probably have to move some of the code in
        # scripts/desktop_unittest.py and scripts/marionette.py to
        # mozharness.mozilla.testing.unittest so we can share it.
        # In the short term, I'm ok with some duplication of code if it
        # expedites things; please file bugs to merge if that happens.

        suite_names = ['mochitest', 'reftest', 'xpcshell']
        suite_name = [x for x in suite_names if x in self.config['test_suite']][0]
        suite = '%s-%s' % (suite_name, self.config['this_chunk'])

        parser = DesktopUnittestOutputParser(suite_category=suite_name,
                                             config=self.config,
                                             log_obj=self.log_obj,
                                             error_list=BaseErrorList)
        return_code = self.run_command(cmd, cwd=cwd,
                                       output_parser=parser)

        tbpl_status, log_level = parser.evaluate_parser(return_code)
        parser.append_tinderboxprint_line(suite_name)

        self.buildbot_status(tbpl_status, level=log_level)
        self.add_summary("The %s suite: %s ran with return status: %s" %
                         (suite_name, suite, tbpl_status),
                         level=log_level)

if __name__ == '__main__':
    emulatorTest = B2GEmulatorTest()
    emulatorTest.run()
