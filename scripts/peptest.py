#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Peptest Mozharness script.
#
# The Initial Developer of the Original Code is
#   Mozilla Corporation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Andrew Halberstadt <halbersa@gmail.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import os
import sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import PythonErrorList
from mozharness.base.log import DEBUG, INFO, WARNING, ERROR, FATAL
from mozharness.base.python import virtualenv_config_options, VirtualenvMixin
from mozharness.base.script import BaseScript
from mozharness.mozilla.buildbot import BuildbotMixin, TBPL_SUCCESS, TBPL_WARNING, TBPL_FAILURE
import urlparse

class PepTest(VirtualenvMixin, BuildbotMixin, BaseScript):
    config_options = [
        [["--appname"],
        {"action": "store",
         "dest": "appname",
         "default": None,
         "help": "Path to the binary (file path or URL) to run the tests on",
        }],
        [["--test-manifest"],
        {"action":"store",
         "dest": "test_manifest",
         "default":None,
         "help": "Path to test manifest to run",
        }],
        [["--peptest-url"],
        {"action": "store",
         "dest": "peptest_url",
         "default": "https://github.com/mozilla/peptest/zipball/master",
         "help": "URL to peptest zip file",
        }],
        [["--test-url"],
        {"action":"store",
         "dest": "test_url",
         "default": None,
         "help": "URL to the zip file containing the actual tests",
        }]] + virtualenv_config_options

    error_list = [
        {'substr': r'''PEP TEST-UNEXPECTED-FAIL''', 'level': ERROR},
        {'substr': r'''PEP ERROR''', 'level': ERROR},
        {'substr': r'''PEP WARNING''', 'level': WARNING},
        {'substr': r'''PEP DEBUG''', 'level': DEBUG},
    ]

    def __init__(self, require_config_file=False):
        super(PepTest, self).__init__(
            config_options=self.config_options,
            all_actions=['clobber',
                         'create-virtualenv',
                         'read-buildbot-config',
                         'get-latest-tinderbox',
                         'create-deps',
                         'run-peptest'],
            default_actions=['clobber',
                             'create-virtualenv',
                             'read-buildbot-config',
                             'create-deps',
                             'run-peptest'],
            require_config_file=require_config_file,
            config={'dependencies': ['mozlog',
                                     'mozinfo',
                                     'mozhttpd',
                                     'mozinstall',
                                     'manifestdestiny',
                                     'mozprofile',
                                     'mozprocess',
                                     'mozrunner'],})
        # these are necessary since self.config is read only
        c = self.config
        dirs = self.query_abs_dirs()
        self.appname = c.get('appname')
        self.symbols = c.get('symbols_path')
        self.test_path = os.path.join(dirs['abs_peptest_dir'],
                                      c['test_manifest'])
        self.test_url = self.config.get('test_url')


    # Helper methods {{{1
    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(PepTest, self).query_abs_dirs()
        c = self.config
        dirs = {}
        dirs['abs_test_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'],
            c.get('test_install_dir', 'tests'))
        dirs['abs_app_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'],
            c.get('app_install_dir', 'application'))
        dirs['abs_mozbase_dir'] = os.path.join(
            dirs['abs_test_install_dir'], "mozbase")
        dirs['abs_peptest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], "peptest")
        if os.path.isabs(c['virtualenv_path']):
            dirs['abs_virtualenv_dir'] = c['virtualenv_path']
        else:
            dirs['abs_virtualenv_dir'] = os.path.join(
                abs_dirs['abs_work_dir'],
                c['virtualenv_path'])
        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def _is_url(self, path):
        """
        Return True if path looks like a URL.
        """
        if path is not None:
            parsed = urlparse.urlparse(path)
            return parsed.scheme != '' or parsed.netloc != ''
        return False

    def _build_arg(self, option, value):
        """
        Build a command line argument
        """
        if not value:
            return []
        return [str(option), str(value)]

    def _install_from_url(self, url, error_level=FATAL):
        """
        Accepts a URL to the application (usually on ftp.m.o)
        Downloads and installs the application
        Returns the binary path
        """
        dirs = self.query_abs_dirs()

        # download the application
        source = self.download_file(url,
                                    error_level=error_level,
                                    parent_dir=dirs['abs_work_dir'])
        if not source:
            return
        source = os.path.realpath(source)

        # install the application
        mozinstall = self.query_python_path("mozinstall")
        cmd = [mozinstall, '--source', source]
        cmd.extend(self._build_arg('--destination',
                   dirs['abs_app_install_dir']))
        binary = self.get_output_from_command(cmd)

        # cleanup
        return binary

    def _install_deps(self):
        """
        Download and install dependencies
        """
        dirs = self.query_abs_dirs()
        python = self.query_python_path()
        # install dependencies
        for module in self.config['dependencies']:
            self.run_command([python, "setup.py", "install"],
                             cwd=os.path.join(dirs['abs_mozbase_dir'], module),
                             error_list=PythonErrorList)

    def _install_peptest(self):
        """
        Download and install peptest
        """
        dirs = self.query_abs_dirs()
        python = self.query_python_path()
        self.run_command([python, "setup.py", "install"],
                         cwd=dirs['abs_peptest_dir'],
                         error_list=PythonErrorList)



    # Actions {{{1
    # create_virtualenv is in VirtualenvMixin.
    # read_buildbot_config is in BuildbotMixin.

    def postflight_read_buildbot_config(self):
        if self.buildbot_config:
            try:
                files = self.buildbot_config['sourcestamp']['changes'][0]['files']
                for file_num in (0, 1):
                    if files[file_num]['name'].endswith('tests.zip'): # yuk
                        # str() because of unicode issues on mac
                        self.test_url = str(files[file_num]['name'])
                    else:
                        self.appname = str(files[file_num]['name'])
            except IndexError, e:
                self.fatal("Unable to set appname+test_url from the the buildbot config: %s!" % str(e))


    def create_deps(self):
        """
        Create virtualenv and install dependencies
        """
        dirs = self.query_abs_dirs()
        if self.test_url:
            bundle = self.download_file(self.test_url,
                                        parent_dir=dirs['abs_work_dir'],
                                        error_level=FATAL)
            unzip = self.query_exe("unzip")
            self.mkdir_p(dirs['abs_test_install_dir'])
            # TODO error_list
            self.run_command([unzip, bundle],
                             cwd=dirs['abs_test_install_dir'])
        self._install_deps()
        self._install_peptest()


    def get_latest_tinderbox(self):
        """
        Find the url to the latest-tinderbox build and
        point the appname at it
        """
        dirs = self.query_abs_dirs()

        if len(self.query_package('getlatesttinderbox')) == 0:
            # install getlatest-tinderbox
            self.info("Installing getlatest-tinderbox")
            pip = self.query_python_path("pip")
            self.run_command(pip + " install GetLatestTinderbox",
                             cwd=dirs['abs_work_dir'],
                             error_list=PythonErrorList)

        # get latest tinderbox build url
        getlatest = self.query_python_path("get-latest-tinderbox")
        cmd = [getlatest, '--latest']
        cmd.extend(self._build_arg('--product',
                   self.config.get('get_latest_tinderbox_product')))
        cmd.extend(self._build_arg('--platform',
                   self.config.get('get_latest_tinderbox_platform')))
        if self.config.get('get_latest_tinderbox_debug_build'):
            cmd.append('--debug')
        url = self.get_output_from_command(cmd)

        # get the symbols url to use for debugging crashes
        cmd = [getlatest, '--url', url, '--symbols']
        self.symbols = self.get_output_from_command(cmd)

        # get the application url to download and install
        cmd = [getlatest, '--url', url]
        self.appname = self.get_output_from_command(cmd)


    def preflight_run_peptest(self):
        if not self.config.get('test_manifest'):
            self.fatal("No test manifest specified. Aborting")

        if not os.path.isfile(self.test_path):
            self.fatal("Test manifest %s does not exist. Aborting" % self.test_path)

        if not self.appname:
            self.fatal("No appname specified! Rerun with appname set, or --get-latest-tinderbox")


    def run_peptest(self):
        """
        Run the peptests
        """
        dirs = self.query_abs_dirs()
        if self._is_url(self.appname):
            self.appname = self._install_from_url(self.appname,
                                                  error_level=FATAL)

        error_list = self.error_list
        error_list.extend(PythonErrorList)

        # build the peptest command arguments
        python = self.query_python_path('python')
        cmd = [python, '-u', os.path.join(dirs['abs_peptest_dir'], 'peptest',
                                          'runpeptests.py')]
        cmd.extend(self._build_arg('--app', self.config.get('app')))
        cmd.extend(self._build_arg('--binary', self.appname))
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
            status = "test failures"
            tbpl_status = TBPL_WARNING
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
