#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import copy
import os
import sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import PythonErrorList
from mozharness.base.log import DEBUG, INFO, WARNING, ERROR
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_FAILURE
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options

class PepTest(TestingMixin, MercurialScript):
    config_options = [
        [["--test-manifest"],
        {"action":"store",
         "dest": "test_manifest",
         "default":None,
         "help": "Path to test manifest to run",
        }],
        [["--use-proxy"],
        {"action": "store_true",
         "dest": "peptest_use_proxy",
         "default": True,
         "help": "Use a local proxy for peptest runs",
        }],
        [["--no-use-proxy"],
        {"action": "store_false",
         "dest": "peptest_use_proxy",
         "help": "Don't use a local proxy for peptest runs",
        }]] + copy.deepcopy(testing_config_options)

    error_list = [
        {'substr': r'''PEP TEST-UNEXPECTED-FAIL''', 'level': ERROR},
        {'substr': r'''PEP ERROR''', 'level': ERROR},
        {'substr': r'''PEP WARNING''', 'level': WARNING},
        {'substr': r'''PEP DEBUG''', 'level': DEBUG},
    ]

    virtualenv_modules = [
     'simplejson',
     {'mozlog': os.path.join('tests', 'mozbase', 'mozlog')},
     {'mozinfo': os.path.join('tests', 'mozbase', 'mozinfo')},
     {'mozhttpd': os.path.join('tests', 'mozbase', 'mozhttpd')},
     {'mozinstall': os.path.join('tests', 'mozbase', 'mozinstall')},
     {'manifestdestiny': os.path.join('tests', 'mozbase', 'manifestdestiny')},
     {'mozprofile': os.path.join('tests', 'mozbase', 'mozprofile')},
     {'mozprocess': os.path.join('tests', 'mozbase', 'mozprocess')},
     {'mozrunner': os.path.join('tests', 'mozbase', 'mozrunner')},
     {'peptest': os.path.join('tests', 'peptest')},
    ]

    def __init__(self, require_config_file=False):
        super(PepTest, self).__init__(
            config_options=self.config_options,
            all_actions=['clobber',
                         'pull',
                         'read-buildbot-config',
                         'download-and-extract',
                         'create-virtualenv',
                         'install',
                         'run-peptest'],
            default_actions=['clobber',
                             'pull',
                             'download-and-extract',
                             'create-virtualenv',
                             'install',
                             'run-peptest'],
            require_config_file=require_config_file,
            config={'virtualenv_modules': self.virtualenv_modules,
                    'require_test_zip': True,})
        # these are necessary since self.config is read only
        c = self.config
        dirs = self.query_abs_dirs()
        self.installer_url = c.get('installer_url')
        self.installer_path = c.get('installer_path')
        self.binary_path = c.get('binary_path')
        self.symbols = c.get('symbols_path')
        self.test_path = os.path.join(dirs['abs_peptest_dir'],
                                      c['test_manifest'])
        self.test_url = self.config.get('test_url')


    # Helper methods {{{1
    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(PepTest, self).query_abs_dirs()
        dirs = {}
        dirs['abs_test_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'tests')
        dirs['abs_app_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'application')
        dirs['abs_mozbase_dir'] = os.path.join(
            dirs['abs_test_install_dir'], "mozbase")
        dirs['abs_peptest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], "peptest")
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



    # Actions {{{1
    # clobber is in BaseScript.

    def pull(self):
        if self.config.get('repos'):
            dirs = self.query_abs_dirs()
            self.vcs_checkout_repos(self.config['repos'],
                                    parent_dir=dirs['abs_work_dir'])


    # read_buildbot_config is in BuildbotMixin.
    # postflight_read_buildbot_config is in TestingMixin.
    # preflight_download_and_extract is in TestingMixin.
    # download_and_extract is in TestingMixin.
    # create_virtualenv is in VirtualenvMixin.
    # preflight_install is in TestingMixin.
    # install is in TestingMixin.


    def preflight_run_peptest(self):
        if not self.config.get('test_manifest'):
            self.fatal("No test manifest specified. Aborting")

        if not os.path.isfile(self.test_path):
            self.fatal("Test manifest %s does not exist. Aborting" % self.test_path)

        if not self.binary_path:
            self.fatal("No binary path specified!\nEither specify |--binary-path PATH| or |--install --installer-url URL|")


    def run_peptest(self):
        """
        Run the peptests
        """
        dirs = self.query_abs_dirs()

        error_list = self.error_list
        error_list.extend(PythonErrorList)

        # build the peptest command arguments
        python = self.query_python_path('python')
        cmd = [python, '-u', os.path.join(dirs['abs_peptest_dir'], 'peptest',
                                          'runpeptests.py')]
        cmd.extend(self._build_arg('--app', self.config.get('app')))
        cmd.extend(self._build_arg('--binary', self.binary_path))
        cmd.extend(self._build_arg('--test-path', self.test_path))
        cmd.extend(self._build_arg('--profile-path',
                   self.config.get('profile_path')))
        cmd.extend(self._build_arg('--timeout', self.config.get('timeout')))
        cmd.extend(self._build_arg('--server-path',
                   self.config.get('server_path')))
        cmd.extend(self._build_arg('--server-port',
                   self.config.get('server_port')))
        cmd.extend(self._build_arg('--tracer-threshold',
                   self.config.get('tracer_threshold')))
        cmd.extend(self._build_arg('--tracer-interval',
                   self.config.get('tracer_interval')))
        cmd.extend(self._build_arg('--symbols-path', self.symbols))
        if self.config.get('peptest_use_proxy'):
            # TODO should these be options? config file settings?
            cmd.extend(['--proxy',
                        os.path.join(dirs['abs_peptest_dir'],
                                     'tests/firefox/server-locations.txt')])
            cmd.append('--proxy-host-dirs')
            cmd.extend(['--server-path',
                        os.path.join(dirs['abs_peptest_dir'],
                                     'tests/firefox/server')])
        if (self.config.get('log_level') in
                           ['debug', 'info', 'warning', 'error']):
            cmd.extend(['--log-level', self.config['log_level'].upper()])

        code = self.run_command(cmd, error_list=error_list)
        # get status and set summary
        level = ERROR
        if code == 0:
            status = "success"
            tbpl_status = TBPL_SUCCESS
            level = INFO
        elif code == 1:
            # XXX hack: perma-green
            # https://bugzilla.mozilla.org/show_bug.cgi?id=737581#c6
            # "Also, can you force this test to go green, regardless of results?"

            #status = "test failures"
            #tbpl_status = TBPL_WARNING
            status = "success"
            tbpl_status = TBPL_SUCCESS
            level = INFO
        else:
            status = "harness failure"
            tbpl_status = TBPL_FAILURE

        # TODO create a better summary for peptest
        #      for now just display return code
        self.add_summary("%s exited with return code %s: %s" % (cmd[0],
                                                                code,
                                                                status),
                         level=level)
        self.buildbot_status(tbpl_status)



if __name__ == '__main__':
    peptest = PepTest()
    peptest.run()
