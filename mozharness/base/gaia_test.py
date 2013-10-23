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

from mozharness.base.errors import TarErrorList, ZipErrorList
from mozharness.base.log import INFO, ERROR, WARNING, FATAL
from mozharness.base.script import PreScriptAction
from mozharness.base.transfer import TransferMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_WARNING, TBPL_FAILURE
from mozharness.mozilla.gaia import GaiaMixin
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options
from mozharness.mozilla.tooltool import TooltoolMixin


class GaiaTest(TestingMixin, TooltoolMixin, MercurialScript, TransferMixin,
    GaiaMixin):
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
        [["--xre-path"],
         {"action": "store",
          "dest": "xre_path",
          "default": "xulrunner-sdk",
          "help": "directory (relative to gaia repo) of xulrunner-sdk"
         }],
        [["--xre-url"],
         {"action": "store",
          "dest": "xre_url",
          "default": None,
          "help": "url of desktop xre archive"
         }],
        [["--npm-registry"],
         {"action": "store",
          "dest": "npm_registry",
          "default": "http://npm-mirror.pub.build.mozilla.org",
          "help": "where to go for node packages"
         }]] + copy.deepcopy(testing_config_options)

    error_list = [
        {'substr': 'FAILED (errors=', 'level': WARNING},
    ]

    virtualenv_modules = [
        'mozinstall',
    ]

    repos = []

    def __init__(self, require_config_file=False):
        super(GaiaTest, self).__init__(
            config_options=self.config_options,
            all_actions=['clobber',
                         'read-buildbot-config',
                         'pull',
                         'download-and-extract',
                         'create-virtualenv',
                         'install',
                         'run-tests'],
            default_actions=['clobber',
                             'pull',
                             'download-and-extract',
                             'create-virtualenv',
                             'install',
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
        dest = dirs['abs_gaia_dir']

        repo = {
          'repo_path': self.config.get('gaia_repo'),
          'revision': 'default',
          'branch': self.config.get('gaia_branch')
        }

        if self.buildbot_config is not None:
            # get gaia commit via hgweb
            repo.update({
              'revision': self.buildbot_config['properties']['revision'],
              'repo_path': 'https://hg.mozilla.org/%s' % self.buildbot_config['properties']['repo_path']
            })

        self.clone_gaia(dest, repo,
                        use_gaia_json=self.buildbot_config is not None)

        super(GaiaTest, self).pull(**kwargs)

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(GaiaTest, self).query_abs_dirs()
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

    @PreScriptAction('create-virtualenv')
    def _pre_create_virtualenv(self, action):
        self.register_virtualenv_module('gaia-unit-tests',
            url=self.query_abs_dirs()['abs_runner_dir'])

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
            parent_dir = os.path.join(parent_dir,
                                      self.config.get('xre_path'))
            if not os.access(parent_dir, os.F_OK):
                self.mkdir_p(parent_dir, error_level=FATAL)
            self.run_command(command,
                             cwd=parent_dir,
                             error_list=ZipErrorList,
                             halt_on_failure=True)

    def download_and_extract(self):
        super(GaiaTest, self).download_and_extract()

        xre_url = self.config.get('xre_url')
        if xre_url:
            dirs = self.query_abs_dirs()
            xulrunner_bin = os.path.join(dirs['abs_gaia_dir'],
                                         self.config.get('xre_path'),
                                         'bin', 'xpcshell')
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

    def run_tests(self):
        """
        Run the test suite.
        """
        pass

    def publish(self, code):
        """
        Publish the results of the test suite.
        """
        if code == 0:
          level = INFO
          status = 'success'
          tbpl_status = TBPL_SUCCESS
        elif code == 10:
          level = INFO
          status = 'test failures'
          tbpl_status = TBPL_WARNING
        else:
          level = ERROR
          status = 'harness failures'
          tbpl_status = TBPL_FAILURE

        self.log('Tests exited with return code %s: %s' % (code, status),
            level=level)
        self.buildbot_status(tbpl_status)
