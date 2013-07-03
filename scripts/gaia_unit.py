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

from mozharness.base.errors import TarErrorList, ZipErrorList, HgErrorList
from mozharness.base.log import INFO, ERROR, WARNING, FATAL
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_WARNING, TBPL_FAILURE
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options
from mozharness.mozilla.testing.unittest import TestSummaryOutputParserHelper
from mozharness.mozilla.tooltool import TooltoolMixin


class GaiaUnitTest(TestingMixin, TooltoolMixin, MercurialScript):
    config_options = [
        [["--gaia-dir"],
         {"action": "store",
          "dest": "gaia_dir",
          "default": None,
          "help": "directory where gaia repo should be cloned"
         }],
        [["--gaia-repo"],
         {"action": "store",
          "dest": "gaia_repo",
          "default": "http://hg.mozilla.org/integration/gaia-central",
          "help": "url of gaia repo to clone"
         }],
        [["--gaia-branch"],
         {"action": "store",
          "dest": "gaia_branch",
          "default": "default",
          "help": "branch of gaia repo to clone"
         }],
        [["--xre-url"],
         {"action": "store",
          "dest": "xre_url",
          "default": None,
          "help": "url of desktop xre archive"
         }]] + copy.deepcopy(testing_config_options)

    error_list = [
        {'substr': 'FAILED (errors=', 'level': WARNING},
    ]

    virtualenv_modules = [
        'mozinstall',
    ]

    repos = []

    def __init__(self, require_config_file=False):
        super(GaiaUnitTest, self).__init__(
            config_options=self.config_options,
            all_actions=['clobber',
                         'read-buildbot-config',
                         'pull',
                         'download-and-extract',
                         'create-virtualenv',
                         'install',
                         'make-gaia',
                         'run-tests'],
            default_actions=['clobber',
                             'pull',
                             'download-and-extract',
                             'create-virtualenv',
                             'install',
                             'make-gaia',
                             'run-tests'],
            require_config_file=require_config_file,
            config={'virtualenv_modules': self.virtualenv_modules,
                    'repos': self.repos,
                    'require_test_zip': False})

        # these are necessary since self.config is read only
        c = self.config
        self.installer_url = c.get('installer_url')
        self.installer_path = c.get('installer_path')
        self.binary_path = c.get('binary_path')

    def pull(self, **kwargs):
        dirs = self.query_abs_dirs()
        repos = copy.deepcopy(self.config.get('repos', []))
        repos.append({'repo': self.config.get('gaia_repo'),
                      'revision': 'default',
                      'dest': 'gaia',
                      'branch': self.config.get('gaia_branch')})
        for repo in repos:
            dest = None
            if repo.get('dest') == 'gaia':
                dest = os.path.dirname(dirs['abs_gaia_dir'])
                repo_dir = os.path.join(dest, 'gaia')

                # purge the repo if it already exists
                if os.access(repo_dir, os.F_OK):
                    cmd = [self.query_exe('hg'),
                           '--config',
                           'extensions.purge=',
                           'purge']
                    if self.run_command(cmd, cwd=repo_dir, error_list=HgErrorList):
                        self.fatal("Unable to purge %s!" % repo_dir)

            kwargs['parent_dir'] = dest
            kwargs['repos'] = [repo]
            super(GaiaUnitTest, self).pull(**kwargs)

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(GaiaUnitTest, self).query_abs_dirs()
        dirs = {}
        gaia_root_dir = self.config.get('gaia_dir')
        if not gaia_root_dir:
            gaia_root_dir = self.config['base_work_dir']
        dirs['abs_gaia_dir'] = os.path.join(gaia_root_dir, 'gaia')
        dirs['abs_runner_dir'] = os.path.join(dirs['abs_gaia_dir'],
                                              'tests', 'python', 'gaia-unit-tests')
        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def create_virtualenv(self, **kwargs):
        super(GaiaUnitTest, self).create_virtualenv(**kwargs)

        dirs = self.query_abs_dirs()
        self.install_module(module='gaia-unit-tests',
                            module_url=dirs['abs_runner_dir'],
                            install_method='pip')

    def _build_arg(self, option, value):
        """
        Build a command line argument
        """
        if not value:
            return []
        return [str(option), str(value)]

    def extract_xre(self, filename, parent_dir=None):
        m = re.search('\.tar\.(bz2|gz)$', filename)
        if m:
            # a xulrunner archive, which has a top-level 'xulrunner-sdk' dir
            command = self.query_exe('tar', return_type='list')
            tar_cmd = "jxf"
            if m.group(1) == "gz":
                tar_cmd = "zxf"
            command.extend([tar_cmd, filename])
            self.run_command(command,
                             cwd=parent_dir,
                             error_list=TarErrorList,
                             halt_on_failure=True)
        else:
            # a tooltool xre.zip
            command = self.query_exe('unzip', return_type='list')
            command.extend(['-q', '-o', filename])
            # Gaia assumes that xpcshell is in a 'xulrunner-sdk' dir, but
            # xre.zip doesn't have a top-level directory name, so we'll
            # create it.
            parent_dir = os.path.join(parent_dir, "xulrunner-sdk")
            if not os.access(parent_dir, os.F_OK):
                self.mkdir_p(parent_dir, error_level=FATAL)
            self.run_command(command,
                             cwd=parent_dir,
                             error_list=ZipErrorList,
                             halt_on_failure=True)

    def download_and_extract(self):
        super(GaiaUnitTest, self).download_and_extract()

        xre_url = self.config.get('xre_url')
        if xre_url:
            dirs = self.query_abs_dirs()
            xulrunner_bin = os.path.join(dirs['abs_gaia_dir'],
                                         'xulrunner-sdk', 'bin', 'xpcshell')
            if not os.access(xulrunner_bin, os.F_OK):
                xre = self.download_file(xre_url, parent_dir=dirs['abs_work_dir'])
                self.extract_xre(xre, parent_dir=dirs['abs_gaia_dir'])

    def install(self):
        # mozinstall doesn't work with B2G desktop builds, but we don't need it
        tar = self.query_exe('tar', return_type='list')
        dirs = self.query_abs_dirs()
        self.run_command(tar + ['jxf', self.installer_path],
                         cwd=dirs['abs_work_dir'],
                         error_list=TarErrorList,
                         halt_on_failure=True)

    def make_gaia(self):
        dirs = self.query_abs_dirs()
        self.run_command(['make'],
                         cwd=dirs['abs_gaia_dir'],
                         env={'DEBUG': '1',
                              'NOFTU': '1',
                              'DESKTOP': '0',
                              'USE_LOCAL_XULRUNNER_SDK': '1'
                              },
                         halt_on_failure=True)

    def run_tests(self):
        """
        Run the Gaia unit tests
        """
        dirs = self.query_abs_dirs()

        # build the testrunner command arguments
        python = self.query_python_path('python')
        cmd = [python, '-u', os.path.join(dirs['abs_runner_dir'],
                                          'gaia_unit_test',
                                          'main.py')]
        cmd.extend(self._build_arg('--binary', os.path.join(dirs['abs_work_dir'],
                                                            'b2g', 'b2g-bin')))
        cmd.extend(self._build_arg('--profile', os.path.join(dirs['abs_gaia_dir'],
                                                             'profile-debug')))

        output_parser = TestSummaryOutputParserHelper(config=self.config,
                                                      log_obj=self.log_obj,
                                                      error_list=self.error_list)
        code = self.run_command(cmd,
                                output_parser=output_parser)

        level = INFO
        if code == 0:
            status = "success"
            tbpl_status = TBPL_SUCCESS
        elif code == 10:
            status = "test failures"
            tbpl_status = TBPL_WARNING
        else:
            status = "harness failures"
            level = ERROR
            tbpl_status = TBPL_FAILURE

        output_parser.print_summary('gaia-unit-tests')

        self.log("Gaia-unit-tests exited with return code %s: %s" % (code, status),
                 level=level)
        self.buildbot_status(tbpl_status)


if __name__ == '__main__':
    gaia_unit_test = GaiaUnitTest()
    gaia_unit_test.run()
