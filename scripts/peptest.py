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

from mozharness.base.errors import PythonErrorList
from mozharness.base.log import DEBUG, INFO, WARNING, ERROR, FATAL
from mozharness.base.python import virtualenv_config_options, VirtualenvMixin
from mozharness.base.script import BaseScript
import urlparse
import tarfile
import zipfile
import platform
import os
import sys

class PepTest(VirtualenvMixin, BaseScript):
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
        [["--mozbase-url"],
        {"action":"store",
         "dest": "mozbase_url",
         "default": "https://github.com/mozilla/mozbase/zipball/master",
         "help": "URL to mozbase zip file",
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
                         'create-deps',
                         'get-latest-tinderbox',
                         'run-peptest'],
            default_actions=['run-peptest'],
            require_config_file=require_config_file,
            config={'dependencies': ['mozlog',
                                     'mozinfo',
                                     'mozhttpd',
                                     'manifestdestiny',
                                     'mozprofile',
                                     'mozprocess',
                                     'mozrunner']})
        # these are necessary since self.config is read only
        self.appname = self.config.get('appname')
        self.symbols = self.config.get('symbols_path')
        self.test_path = self.config.get('test_manifest')

    def create_deps(self):
        """
        Create virtualenv and install dependencies
        """
        self.create_virtualenv()
        self._install_deps()
        self._install_peptest()

    def _install_deps(self):
        """
        Download and install dependencies
        """
        # download and extract mozbase
        work_dir = self.query_abs_dirs()['abs_work_dir']

        mozbase = self.config.get('mozbase_path');
        if not mozbase:
            self.fatal("No path to mozbase specified. Aborting")

        if self._is_url(mozbase):
            mozbase = self.download_file(mozbase,
                      file_name=os.path.join(work_dir, 'mozbase'),
                      error_level=FATAL)

        if os.path.isfile(mozbase):
            mozbase = self.extract(mozbase, delete=True, error_level=FATAL)[0]

        python = self.query_python_path()
        # install dependencies
        for module in self.config['dependencies']:
            self.run_command(python + " setup.py install",
                             cwd=os.path.join(mozbase, module),
                             error_list=PythonErrorList)
        self.rmtree(mozbase)

    def _install_peptest(self):
        """
        Download and install peptest
        """
        # download and extract peptest
        work_dir = self.query_abs_dirs()['abs_work_dir']

        peptest = self.config.get('peptest_path')
        if not peptest:
            self.fatal("No path to peptest specified. Aborting")

        if self._is_url(peptest):
            peptest = self.download_file(peptest,
                      file_name=os.path.join(work_dir, 'peptest'),
                      error_level=FATAL)

        if os.path.isfile(peptest):
            peptest = self.extract(peptest, delete=True, error_level=FATAL)[0]

        python = self.query_python_path()
        self.run_command(python + " setup.py install",
                         cwd=peptest,
                         error_list=PythonErrorList)
        self.rmtree(peptest)

    def get_latest_tinderbox(self):
        """
        Find the url to the latest-tinderbox build and
        point the appname at it
        """
        if not self.query_python_path():
            self.create_virtualenv()
        dirs = self.query_abs_dirs()

        if len(self.query_package('getlatesttinderbox')) == 0:
            # install getlatest-tinderbox
            self.info("Installing getlatest-tinderbox")
            pip = self.query_python_path("pip")
            if not pip:
                self.error("No application named 'pip' installed")
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

        if self.config.get('test_url'):
            bundle = self.download_file(self.config['test_url'])
            files = self.extract(bundle,
                                  extdir=self.config.get('test_install_dir'),
                                  delete=True)
            self.test_path = os.path.join(files[0],
                                          self.config['test_manifest'])

        if not os.path.isfile(self.test_path):
            self.fatal("Test manifest does not exist. Aborting")

        if "create-deps" not in self.actions:
            # ensure all the dependencies are installed
            for module in self.config['dependencies'] + ['peptest']:
                if len(self.query_package(module)) == 0:
                    self.action_message("Dependencies missing, " +
                                        "running create-deps step")
                    self.create_deps()
                    break

        if not self.appname:
            self.action_message("No appname specified, " +
                                "running get-latest-tinderbox step")
            self.get_latest_tinderbox()


    def run_peptest(self):
        """
        Run the peptests
        """
        if self._is_url(self.appname):
            self.appname = self._install_from_url(self.appname,
                                                  error_level=FATAL)

        error_list = self.error_list
        error_list.extend(PythonErrorList)

        # build the peptest command arguments
        peptest = self.query_python_path('peptest')
        cmd = [peptest]
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

        code = self.run_command(cmd,
                                error_list=error_list)
        # get status and set summary
        level = ERROR
        if code == 0:
            status = "success"
            level = INFO
        elif code == 1:
            status = "test failures"
        else:
            status = "harness failure"

        # TODO create a better summary for peptest
        #      for now just display return code
        self.add_summary("%s exited with return code %s: %s" % (cmd[0],
                                                                code,
                                                                status))

    def _build_arg(self, option, value):
        """
        Build a command line argument
        """
        if not value:
            return []
        return [str(option), str(value)]

    def _install_from_url(self, url, error_level=ERROR):
        """
        Accepts a URL to the application (usually on ftp.m.o)
        Downloads and installs the application
        Returns the binary path
        """
        dirs = self.query_abs_dirs()
        # ensure mozinstall is available
        if len(self.query_package("mozinstall")) == 0:
            # install mozinstall
            self.info("Installing mozinstall")
            pip = self.query_python_path("pip")
            if not pip:
                self.log("No application named 'pip' installed",
                         level=error_level)
            self.run_command(pip + " install mozInstall",
                             cwd=dirs['abs_work_dir'],
                             error_list=PythonErrorList)

        # download the application
        source = os.path.realpath(self.download_file(url))

        # install the application
        mozinstall = self.query_python_path("mozinstall")
        cmd = [mozinstall, '--source', source]
        cmd.extend(self._build_arg('--destination',
                   self.config.get('application_install_dir')))
        binary = self.get_output_from_command(cmd)

        # cleanup
        self.rmtree(source)
        return binary

    def _is_url(self, path):
        """
        Return True if path looks like a URL.
        """
        if path is not None:
            parsed = urlparse.urlparse(path)
            return parsed.scheme != '' or parsed.netloc != ''
        return False




if __name__ == '__main__':
    peptest = PepTest()
    peptest.run()
