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
from mozharness.base.log import ERROR, FATAL
from mozharness.base.script import BaseScript
from mozharness.base.vcs.vcsbase import VCSMixin
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options
from mozharness.mozilla.testing.unittest import DesktopUnittestOutputParser, EmulatorMixin
from mozharness.mozilla.tooltool import TooltoolMixin

from mozharness.mozilla.testing.device import ADBDeviceHandler

class Androidx86EmulatorTest(TestingMixin, TooltoolMixin, EmulatorMixin, VCSMixin, BaseScript):
    test_suites = ('mochitest', 'robocop', 'reftest', 'jsreftest', 'crashtest')
    config_options = [
        [["--type"],
        {"action": "store",
         "dest": "test_type",
         "default": "browser",
         "help": "The type of tests to run",
        }],
        [["--xre-url"],
        {"action": "store",
         "dest": "xre_url",
         "default": None,
         "help": "URL to the desktop xre zip",
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
         "choices": test_suites,
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

    virtualenv_requirements = [
    ]

    virtualenv_modules = [
    ]

    def __init__(self, require_config_file=False):
        super(Androidx86EmulatorTest, self).__init__(
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
                'virtualenv_requirements': self.virtualenv_requirements,
                'require_test_zip': True,
                # IP address of the host as seen from the emulator
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
        abs_dirs = super(Androidx86EmulatorTest, self).query_abs_dirs()
        dirs = {}
        dirs['abs_test_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'tests')
        dirs['abs_xre_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'xre')
        dirs['abs_mochitest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'mochitest')
        dirs['abs_modules_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'modules')
        dirs['abs_reftest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'reftest')
        dirs['abs_xpcshell_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'xpcshell')
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
        super(Androidx86EmulatorTest, self).download_and_extract()
        dirs = self.query_abs_dirs()
        if self.config.get('download_minidump_stackwalk'):
            self.install_minidump_stackwalk()

        self.download_file(self.config['robocop_url'], file_name='robocop.apk',
                                    parent_dir=dirs['abs_mochitest_dir'],
                                    error_level=FATAL)

        self.download_file(self.config['symbols_url'], file_name='crashreporter-symbols.zip',
                                    parent_dir=dirs['abs_work_dir'],
                                    error_level=FATAL)

        self.mkdir_p(dirs['abs_xre_dir'])
        self._download_unzip(self.config['xre_url'],
                             dirs['abs_xre_dir'])

    def preflight_install(self):
        # in the base class, this checks for mozinstall, but we don't use it
        pass

    def install(self):
        dirs = self.query_abs_dirs()
        config={'device-id': self.config['device_id'], 'enable_automation': True, 'device_package_name': self.config['application']}

        dh = ADBDeviceHandler(config=config)
        dh.device_id = self.config['device_id']

        #install fennec
        dh.install_app(self.installer_path)

        #also install robocop apk if required
        if self.config['test_suite'] == 'robocop':
            config['device_package_name'] = 'org.mozilla.roboexample.test'
            robocop_path = os.path.join(dirs['abs_mochitest_dir'], 'robocop.apk')
            dh.install_app(robocop_path)


    def _build_mochitest_args(self):
        c = self.config
        dirs = self.query_abs_dirs()
        python = self.query_python_path('python')
        cmd = [
            python, os.path.join(dirs['abs_mochitest_dir'], 'runtestsremote.py'),
            '--autorun',
            '--close-when-done',
            '--dm_trans=sut',
            '--console-level', 'INFO',
            '--app', c['application'],
            '--remote-webserver', c['remote_webserver'],
            '--run-only-tests', self.test_manifest,
            '--xre-path', os.path.join(dirs['abs_xre_dir'], 'bin'),
            '--deviceIP', self.config['device_ip'],
            '--devicePort', self.config['device_port'],
            '--http-port', self.config['http_port'],
            '--ssl-port', self.config['ssl_port']
        ]
        cmd.extend(self._build_arg('--total-chunks', c.get('total_chunks')))
        cmd.extend(self._build_arg('--this-chunk', c.get('this_chunk')))
        cmd.extend(self._build_arg('--symbols-path', 'crashreporter-symbols.zip'))

        return cmd

    def _build_robocop_args(self):
        c = self.config
        dirs = self.query_abs_dirs()
        python = self.query_python_path('python')
        cmd = [
            python, os.path.join(dirs['abs_mochitest_dir'], 'runtestsremote.py'),
            '--robocop-path=.',
            '--robocop-ids=fennec_ids.txt',
            '--dm_trans=sut',
            '--console-level', 'INFO',
            '--app', c['application'],
            '--remote-webserver', c['remote_webserver'],
            '--robocop', self.test_manifest,
            '--xre-path', os.path.join(dirs['abs_xre_dir'], 'bin'),
            '--deviceIP', self.config['device_ip'],
            '--devicePort', self.config['device_port'],
            '--http-port', self.config['http_port'],
            '--ssl-port', self.config['ssl_port']
        ]
        cmd.extend(self._build_arg('--total-chunks', c.get('total_chunks')))
        cmd.extend(self._build_arg('--this-chunk', c.get('this_chunk')))
        cmd.extend(self._build_arg('--symbols-path', 'crashreporter-symbols.zip'))

        return cmd

    def _build_reftest_args(self, is_jsreftest=False):
        c = self.config
        dirs = self.query_abs_dirs()
        python = self.query_python_path('python')

        cmd = [
            python, 'remotereftest.py',
            '--app=' + self.config['application'],
            '--ignore-window-size',
            '--remote-webserver', c['remote_webserver'],
            '--xre-path', os.path.join(dirs['abs_xre_dir'], 'bin'),
            '--deviceIP', self.config['device_ip'],
            '--devicePort', self.config['device_port'],
            '--http-port', self.config['http_port'],
            '--ssl-port', self.config['ssl_port']
        ]

        cmd.extend(self._build_arg('--total-chunks', c.get('total_chunks')))
        cmd.extend(self._build_arg('--this-chunk', c.get('this_chunk')))
        cmd.extend(self._build_arg('--symbols-path', 'crashreporter-symbols.zip'))

        # extra argument only for jsreftest
        if is_jsreftest:
            cmd.append('--extra-profile-file=jsreftest/tests/user.js')

        cmd.append(self.test_manifest)
        return cmd

    def _build_xpcshell_args(self):
        pass

    def _query_adb(self):
        return self.which('adb') or \
               os.getenv('ADB_PATH')

    def preflight_run_tests(self):
        super(Androidx86EmulatorTest, self).preflight_run_tests()
        suite = self.config['test_suite']
        # set default test manifest by suite if none specified
        if not self.test_manifest:
            if suite == 'mochitest':
                self.test_manifest = 'androidx86.json'
            elif suite == 'robocop':
                self.test_manifest = 'robocop.ini'
            elif suite == 'reftest':
                self.test_manifest = os.path.join('tests', 'layout',
                                                  'reftests', 'reftest.list')
            elif suite == 'crashtest':
                self.test_manifest = os.path.join('tests', 'testing',
                                                  'crashtest', 'crashtests.list')
            elif suite == 'jsreftest':
                self.test_manifest = os.path.join('..','jsreftest', 'tests', 'jstests.list')

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
        elif self.config['test_suite'] == 'robocop':
            cmd = self._build_robocop_args()
            cwd = dirs['abs_mochitest_dir']
        elif self.config['test_suite'] in ('reftest', 'crashtest'):
            cmd = self._build_reftest_args()
            cwd = dirs['abs_reftest_dir']
        elif self.config['test_suite'] == 'jsreftest':
            cmd = self._build_reftest_args(True)
            cwd = dirs['abs_reftest_dir']
        elif self.config['test_suite'] == 'xpcshell':
            cmd = self._build_xpcshell_args()
            cwd = dirs['abs_xpcshell_dir']
        else:
            self.fatal("Don't know how to run --test-suite '%s'!" % self.config['test_suite'])

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
                                       output_parser=parser,
                                       success_codes=success_codes)

        tbpl_status, log_level = parser.evaluate_parser(return_code)
        parser.append_tinderboxprint_line(suite_name)

        self.buildbot_status(tbpl_status, level=log_level)
        self.log("The %s suite: %s ran with return status: %s" %
                 (suite_name, suite, tbpl_status), level=log_level)

if __name__ == '__main__':
    emulatorTest = Androidx86EmulatorTest()
    emulatorTest.run_and_exit()
