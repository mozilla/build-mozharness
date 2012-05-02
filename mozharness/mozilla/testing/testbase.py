#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import copy
import os

from mozharness.base.log import FATAL
from mozharness.base.python import virtualenv_config_options, VirtualenvMixin
from mozharness.mozilla.buildbot import BuildbotMixin

testing_config_options = [
    [["--installer-url"],
    {"action": "store",
     "dest": "installer_url",
     "default": None,
     "help": "URL to the installer to install",
    }],
    [["--installer-path"],
    {"action": "store",
     "dest": "installer_path",
     "default": None,
     "help": "Path to the installer to install.  This is set automatically if run with --download-and-extract.",
    }],
    [["--binary-path"],
    {"action": "store",
     "dest": "binary_path",
     "default": None,
     "help": "Path to installed binary.  This is set automatically if run with --install.",
    }],
    [["--test-url"],
    {"action":"store",
     "dest": "test_url",
     "default": None,
     "help": "URL to the zip file containing the actual tests",
    }]
] + copy.deepcopy(virtualenv_config_options)



# TestingMixin {{{1
class TestingMixin(VirtualenvMixin, BuildbotMixin):
    """
    The steps to identify + download the proper bits for [browser] unit
    tests and Talos.
    """

    installer_url = None
    installer_path = None
    binary_path = None
    test_url = None
    test_zip_path = None

    # read_buildbot_config is in BuildbotMixin.

    def postflight_read_buildbot_config(self):
        """
        Determine which files to download from the buildprops.json file
        created via the buildbot ScriptFactory.
        """
        if self.buildbot_config:
            c = self.config
            message = "Unable to set %s from the buildbot config"
            try:
                files = self.buildbot_config['sourcestamp']['changes'][0]['files']
                expected_length = 1
                if c.get("require_test_zip"):
                    expected_length = 2
                actual_length = len(files)
                if actual_length != expected_length:
                    self.fatal("Unexpected number of files in buildbot config %s: %d != %d!" % (c['buildbot_json_path'], actual_length, expected_length))
                for f in files:
                    if f['name'].endswith('tests.zip'): # yuk
                        # str() because of unicode issues on mac
                        self.test_url = str(f['name'])
                        self.info("Found test url %s." % self.test_url)
                    else:
                        self.installer_url = str(f['name'])
                        self.info("Found installer url %s." % self.installer_url)
            except IndexError, e:
                if c.get("require_test_zip"):
                    message = message % ("installer_url+test_url")
                else:
                    message = message % ("installer_url")
                self.fatal("%s: %s!" % (message, str(e)))
            missing = []
            if not self.installer_url:
                missing.append("installer_url")
            if c.get("require_test_zip") and not self.test_url:
                missing.append("test_url")
            if missing:
                self.fatal("%s!" % (message % ('+'.join(missing))))
        else:
            self.fatal("self.buildbot_config isn't set after running read_buildbot_config!")


    def preflight_download_and_extract(self):
        message = ""
        if not self.installer_url:
            message += """installer_url isn't set!

You can set this by:

1. specifying --installer-url URL, or
2. running via buildbot and running the read-buildbot-config action

"""
        if self.config.get("require_test_zip") and not self.test_url:
            message += """test_url isn't set!

You can set this by:

1. specifying --test-url URL, or
2. running via buildbot and running the read-buildbot-config action

"""
        if message:
            self.fatal(message + "Can't run download-and-extract... exiting")

    def _download_test_zip(self):
        dirs = self.query_abs_dirs()
        file_name = None
        if self.test_zip_path:
            file_name = self.test_zip_path
        source = self.download_file(self.test_url, file_name=file_name,
                                    parent_dir=dirs['abs_work_dir'],
                                    error_level=FATAL)
        self.test_zip_path = os.path.realpath(source)

    def _extract_test_zip(self):
        dirs = self.query_abs_dirs()
        unzip = self.query_exe("unzip")
        test_install_dir = dirs.get('abs_test_install_dir',
                                    os.path.join(dirs['abs_work_dir'], 'tests'))
        self.mkdir_p(test_install_dir)
        # TODO error_list
        self.run_command([unzip, self.test_zip_path],
                         cwd=test_install_dir)

    def _download_installer(self):
        file_name = None
        if self.installer_path:
            file_name = self.installer_path
        dirs = self.query_abs_dirs()
        source = self.download_file(self.installer_url, file_name=file_name,
                                    parent_dir=dirs['abs_work_dir'],
                                    error_level=FATAL)
        self.installer_path = os.path.realpath(source)

    def download_and_extract(self):
        """
        Create virtualenv and install dependencies
        """
        if self.test_url:
            self._download_test_zip()
            self._extract_test_zip()
        self._download_installer()


    # create_virtualenv is in VirtualenvMixin.

    def preflight_install(self):
        if not self.installer_path:
            self.fatal("""installer_path isn't set!

You can set this by:

1. specifying --installer-path PATH, or
2. running the download-and-extract action
""")
        if not self.is_python_package_installed("mozInstall"):
            self.fatal("""Can't call install() without mozinstall!
Did you run with --create-virtualenv? Is mozinstall in virtualenv_modules?""")

    def install(self):
        """ Dependent on mozinstall """
        # install the application
        mozinstall = self.query_python_path("mozinstall")
        dirs = self.query_abs_dirs()
        target_dir = dirs.get('abs_app_install_dir',
                              os.path.join(dirs['abs_work_dir'],
                             'application'))
        self.mkdir_p(target_dir)
        cmd = [mozinstall, '--source', self.installer_path]
        cmd.extend(['--destination', target_dir])
        # TODO we'll need some error checking here
        self.binary_path = self.get_output_from_command(cmd)
