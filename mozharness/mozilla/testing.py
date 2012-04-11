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
    test_path = None
    test_url = None

    # read_buildbot_config is in BuildbotMixin.

    def postflight_read_buildbot_config(self):
        """
        Determine which files to download from the buildprops.json file
        created via the buildbot ScriptFactory.
        """
        if self.buildbot_config:
            try:
                files = self.buildbot_config['sourcestamp']['changes'][0]['files']
                for file_num in (0, 1):
                    if files[file_num]['name'].endswith('tests.zip'): # yuk
                        # str() because of unicode issues on mac
                        self.test_url = str(files[file_num]['name'])
                        self.info("Found test url %s." % self.test_url)
                    else:
                        self.installer_url = str(files[file_num]['name'])
                        self.info("Found installer url %s." % self.installer_url)
            except IndexError, e:
                self.fatal("Unable to set installer_url+test_url from the the buildbot config: %s!" % str(e))


    def preflight_download_and_extract(self):
        message = ""
        if not self.installer_url:
            message += """installer_url isn't set!

You can set this by:

1. specifying --installer-url URL, or
2. running via buildbot and running the read-buildbot-config action

"""
        if not self.test_url:
            message += """test_url isn't set!

You can set this by:

1. specifying --test-url URL, or
2. running via buildbot and running the read-buildbot-config action

"""
        if message:
            self.fatal(message + "Can't run download-and-extract... exiting")

    def download_and_extract(self):
        """
        Create virtualenv and install dependencies
        """
        dirs = self.query_abs_dirs()
        bundle = self.download_file(self.test_url,
                                    parent_dir=dirs['abs_work_dir'],
                                    error_level=FATAL)
        unzip = self.query_exe("unzip")
        test_install_dir = dirs.get('abs_test_install_dir',
                                    os.path.join(dirs['abs_work_dir'], 'tests'))
        self.mkdir_p(test_install_dir)
        # TODO error_list
        self.run_command([unzip, bundle],
                         cwd=test_install_dir)
        source = self.download_file(self.installer_url, error_level=FATAL,
                                    parent_dir=dirs['abs_work_dir'])
        self.installer_path = os.path.realpath(source)


    # create_virtualenv is in VirtualenvMixin.

    def preflight_install(self):
        if not self.installer_path:
            self.fatal("""installer_path isn't set!

You can set this by:

1. specifying --installer-path PATH, or
2. running the download-and-extract action
""")
        if not self.query_python_package("mozinstall"):
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
