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

from mozharness.base.errors import TarErrorList
from mozharness.base.log import INFO, ERROR, WARNING
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_WARNING, TBPL_FAILURE
from mozharness.mozilla.testing.errors import LogcatErrorList
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options
from mozharness.mozilla.testing.unittest import EmulatorMixin, TestSummaryOutputParserHelper
from mozharness.mozilla.tooltool import TooltoolMixin


class MarionetteOutputParser(TestSummaryOutputParserHelper):
    """
    A class that extends TestSummaryOutputParserHelper such that it can parse
    if gecko did not install properly
    """

    bad_gecko_install = re.compile(r'Error installing gecko!')

    def __init__(self, **kwargs):
        self.install_gecko_failed = False
        super(MarionetteOutputParser, self).__init__(**kwargs)

    def parse_single_line(self, line):
        if self.bad_gecko_install.search(line):
            self.install_gecko_failed = True
        super(MarionetteOutputParser, self).parse_single_line(line)

class MarionetteTest(TestingMixin, TooltoolMixin, EmulatorMixin, MercurialScript):
    config_options = [
        [["--test-type"],
        {"action": "store",
         "dest": "test_type",
         "default": "browser",
         "help": "The type of tests to run",
        }],
        [["--marionette-address"],
        {"action": "store",
         "dest": "marionette_address",
         "default": None,
         "help": "The host:port of the Marionette server running inside Gecko.  Unused for emulator testing",
        }],
        [["--emulator"],
        {"action": "store",
         "type": "choice",
         "choices": ['arm'],
         "dest": "emulator",
         "default": None,
         "help": "Use an emulator for testing",
        }],
        [["--gaiatest"],
        {"action": "store_true",
         "dest": "gaiatest",
         "default": False,
         "help": "Runs gaia-ui-tests by pulling down the test repo and invoking "
                 "gaiatest's runtests.py rather than Marionette's."
        }],
        [["--test-manifest"],
        {"action": "store",
         "dest": "test_manifest",
         "default": "unit-tests.ini",
         "help": "Path to test manifest to run relative to the Marionette "
                 "tests directory",
        }]] + copy.deepcopy(testing_config_options)

    error_list = [
        {'substr': 'FAILED (errors=', 'level': WARNING},
        {'substr': r'''Could not successfully complete transport of message to Gecko, socket closed''', 'level': ERROR},
        {'substr': 'Timeout waiting for marionette on port', 'level': ERROR},
        {'regex': re.compile(r'''(Timeout|NoSuchAttribute|Javascript|NoSuchElement|XPathLookup|NoSuchWindow|StaleElement|ScriptTimeout|ElementNotVisible|NoSuchFrame|InvalidElementState|NoAlertPresent|InvalidCookieDomain|UnableToSetCookie|InvalidSelector|MoveTargetOutOfBounds)Exception'''), 'level': ERROR},
    ]

    virtualenv_modules = None
    repos = []

    gaia_ui_tests_repo = {'repo': 'http://hg.mozilla.org/integration/gaia-ui-tests/',
                          'revision': 'default',
                          'dest': 'gaia-ui-tests',
                          'branch': 'default'}

    def __init__(self, require_config_file=False):
        super(MarionetteTest, self).__init__(
            config_options=self.config_options,
            all_actions=['clobber',
                         'read-buildbot-config',
                         'pull',
                         'download-and-extract',
                         'create-virtualenv',
                         'install',
                         'run-marionette'],
            default_actions=['clobber',
                             'pull',
                             'download-and-extract',
                             'create-virtualenv',
                             'install',
                             'run-marionette'],
            require_config_file=require_config_file,
            config={'require_test_zip': True,})

        # these are necessary since self.config is read only
        c = self.config
        self.installer_url = c.get('installer_url')
        self.installer_path = c.get('installer_path')
        self.binary_path = c.get('binary_path')
        self.test_url = c.get('test_url')

    def _pre_config_lock(self, rw_config):
        if not self.config.get('emulator') and not self.config.get('marionette_address'):
                self.fatal("You need to specify a --marionette-address for non-emulator tests! (Try --marionette-address localhost:2828 )")

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(MarionetteTest, self).query_abs_dirs()
        dirs = {}
        dirs['abs_test_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'tests')
        dirs['abs_marionette_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'marionette', 'marionette')
        dirs['abs_marionette_tests_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'marionette', 'tests', 'testing',
            'marionette', 'client', 'marionette', 'tests')
        dirs['abs_gecko_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'gecko')
        dirs['abs_emulator_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'emulator')
        dirs['abs_gaiatest_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'gaia-ui-tests')
        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def create_virtualenv(self, **kwargs):
        if self.tree_config.get('use_puppetagain_packages'):
            self.virtualenv_modules = [
                'mozinstall',
                { 'marionette': os.path.join('tests', 'marionette') },
            ]
        else:
            mozbase_dir = os.path.join('tests', 'mozbase')
            # XXX Bug 879765: Dependent modules need to be listed before parent
            # modules, otherwise they will get installed from the pypi server.
            self.virtualenv_modules = [
                { 'manifestparser': os.path.join(mozbase_dir, 'manifestdestiny') },
                { 'mozfile': os.path.join(mozbase_dir, 'mozfile') },
                { 'mozlog': os.path.join(mozbase_dir, 'mozlog') },
                { 'moznetwork': os.path.join(mozbase_dir, 'moznetwork') },
                { 'mozinfo': os.path.join(mozbase_dir, 'mozinfo') },
                { 'mozhttpd': os.path.join(mozbase_dir, 'mozhttpd') },
                { 'mozcrash': os.path.join(mozbase_dir, 'mozcrash') },
                { 'mozinstall': os.path.join(mozbase_dir, 'mozinstall') },
                { 'mozdevice': os.path.join(mozbase_dir, 'mozdevice') },
                { 'mozprofile': os.path.join(mozbase_dir, 'mozprofile') },
                { 'mozprocess': os.path.join(mozbase_dir, 'mozprocess') },
                { 'mozrunner': os.path.join(mozbase_dir, 'mozrunner') },
                { 'marionette': os.path.join('tests', 'marionette') },
            ]

        super(MarionetteTest, self).create_virtualenv(modules=self.virtualenv_modules, **kwargs)

        if self.config.get('gaiatest'):
            dirs = self.query_abs_dirs()
            self.install_module(module='gaia-ui-tests',
                                module_url=dirs['abs_gaiatest_dir'],
                                install_method='pip')

    def pull(self, **kwargs):
        repos = copy.deepcopy(self.config.get('repos', []))
        if self.config.get('gaiatest'):
            repos.append(self.config.get("gaia_ui_tests_repo", self.gaia_ui_tests_repo))
        kwargs['repos'] = repos
        super(MarionetteTest, self).pull(**kwargs)

    def _build_arg(self, option, value):
        """
        Build a command line argument
        """
        if not value:
            return []
        return [str(option), str(value)]

    def download_and_extract(self):
        super(MarionetteTest, self).download_and_extract()
        if self.config.get('emulator'):
            dirs = self.query_abs_dirs()
            self.workdir = dirs['abs_work_dir']
            self.install_emulator()
            self.mkdir_p(dirs['abs_gecko_dir'])
            tar = self.query_exe('tar', return_type='list')
            self.run_command(tar + ['zxf', self.installer_path],
                             cwd=dirs['abs_gecko_dir'],
                             error_list=TarErrorList,
                             halt_on_failure=True)
            if self.config.get('download_minidump_stackwalk'):
                self.install_minidump_stackwalk()

    def install(self):
        if self.config.get('emulator'):
            self.info("Emulator tests; skipping.")
        elif self.config.get('gaiatest'):
            # mozinstall doesn't work with B2G desktop builds, but we don't need it
            tar = self.query_exe('tar', return_type='list')
            dirs = self.query_abs_dirs()
            self.run_command(tar + ['jxf', self.installer_path],
                             cwd=dirs['abs_work_dir'],
                             error_list=TarErrorList,
                             halt_on_failure=True)
        else:
            super(MarionetteTest, self).install()

    def run_marionette(self):
        """
        Run the Marionette tests
        """
        dirs = self.query_abs_dirs()

        # build the marionette command arguments
        python = self.query_python_path('python')
        if self.config.get('gaiatest'):
            # write a testvars.json file
            testvars = os.path.join(dirs['abs_gaiatest_dir'],
                                    'gaiatest', 'testvars.json')
            with open(testvars, 'w') as f:
                f.write('{"acknowledged_risks": true, "skip_warning": true}')

            # gaia-ui-tests on B2G desktop builds
            cmd = [python, '-u', os.path.join(dirs['abs_gaiatest_dir'],
                                              'gaiatest',
                                              'runtests.py')]
            cmd.extend(self._build_arg('--binary', os.path.join(dirs['abs_work_dir'],
                                                                'b2g', 'b2g')))
            cmd.extend(self._build_arg('--address', self.config['marionette_address']))
            cmd.extend(self._build_arg('--type', self.config['test_type']))
            cmd.extend(self._build_arg('--testvars', testvars))
            manifest = os.path.join(dirs['abs_gaiatest_dir'], 'gaiatest', 'tests',
                                    'manifest.ini')
            cmd.append(manifest)
        else:
            # Marionette or Marionette-webapi tests
            cmd = [python, '-u', os.path.join(dirs['abs_marionette_dir'],
                                              'runtests.py')]

            if self.config.get('emulator'):
                # emulator Marionette-webapi tests
                cmd.extend(self._build_arg('--logcat-dir', dirs['abs_work_dir']))
                cmd.extend(self._build_arg('--emulator', self.config['emulator']))
                cmd.extend(self._build_arg('--gecko-path',
                                           os.path.join(dirs['abs_gecko_dir'], 'b2g')))
                cmd.extend(self._build_arg('--homedir',
                                           os.path.join(dirs['abs_emulator_dir'],
                                                        'b2g-distro')))
                cmd.extend(self._build_arg('--symbols-path', self.symbols_path))
            else:
                # desktop Marionette tests
                cmd.extend(self._build_arg('--binary', self.binary_path))
                cmd.extend(self._build_arg('--address', self.config['marionette_address']))

            cmd.extend(self._build_arg('--type', self.config['test_type']))
            manifest = os.path.join(dirs['abs_marionette_tests_dir'],
                                    self.config['test_manifest'])
            cmd.append(manifest)

        env = {}
        if self.query_minidump_stackwalk():
            env['MINIDUMP_STACKWALK'] = self.minidump_stackwalk_path
        env = self.query_env(partial_env=env)

        for i in range(0, 5):
            # We retry the run because sometimes installing gecko on the
            # emulator can cause B2G not to restart properly - Bug 812935.
            marionette_parser = MarionetteOutputParser(config=self.config,
                                                       log_obj=self.log_obj,
                                                       error_list=self.error_list)
            code = self.run_command(cmd, env=env,
                                    output_parser=marionette_parser)
            if not marionette_parser.install_gecko_failed:
                break
        else:
            self.fatal("Failed to install gecko 5 times in a row, aborting")

        level = INFO
        if code == 0 and marionette_parser.passed > 0 and marionette_parser.failed == 0:
            status = "success"
            tbpl_status = TBPL_SUCCESS
        elif code == 10 and marionette_parser.failed > 0:
            status = "test failures"
            tbpl_status = TBPL_WARNING
        else:
            status = "harness failures"
            level = ERROR
            tbpl_status = TBPL_FAILURE

        # dump logcat output if there were failures
        if self.config.get('emulator') and (marionette_parser.failed != "0" or 'T-FAIL' in marionette_parser.tsummary):
            logcat = os.path.join(dirs['abs_work_dir'], 'emulator-5554.log')
            if os.access(logcat, os.F_OK):
                self.info('dumping logcat')
                self.run_command(['cat', logcat], error_list=LogcatErrorList)
            else:
                self.info('no logcat file found')

        marionette_parser.print_summary('marionette')

        self.log("Marionette exited with return code %s: %s" % (code, status),
                 level=level)
        self.buildbot_status(tbpl_status)


if __name__ == '__main__':
    marionetteTest = MarionetteTest()
    marionetteTest.run()
