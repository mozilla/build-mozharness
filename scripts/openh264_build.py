#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
import sys
import os

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

# import the guts
from mozharness.base.vcs.vcsbase import VCSScript
from mozharness.base.log import ERROR


class OpenH264Build(VCSScript):
    all_actions = [
        'clobber',
        'checkout-sources',
        'build',
        'test',
        'upload',
    ]

    default_actions = [
        'checkout-sources',
        'build',
        'test',
    ]

    config_options = [
        [["--repo"], {
            "dest": "repo",
            "help": "OpenH264 repository to use",
            "default": "https://github.com/cisco/openh264.git"
        }],
        [["--rev"], {
            "dest": "revision",
            "help": "revision to checkout",
            "default": "master"
        }],
        [["--debug"], {
            "dest": "debug_build",
            "action": "store_true",
            "help": "Do a debug build",
        }],
        [["--64"], {
            "dest": "64bit",
            "action": "store_true",
            "help": "Do a 64-bit build",
            "default": True,
        }],
        [["--32"], {
            "dest": "64bit",
            "action": "store_false",
            "help": "Do a 32-bit build",
        }],
        [["--os"], {
            "dest": "operating_system",
            "help": "Specify the operating system to build for",
        }],
    ]

    def __init__(self, require_config_file=False, config={},
                 all_actions=all_actions,
                 default_actions=default_actions):

        # Default configuration
        default_config = {
            'debug_build': False,
        }
        default_config.update(config)

        VCSScript.__init__(
            self,
            config_options=self.config_options,
            require_config_file=require_config_file,
            config=default_config,
            all_actions=all_actions,
            default_actions=default_actions,
        )

    def query_make_params(self):
        retval = []
        if self.config['debug_build']:
            retval.append('BUILDTYPE=Debug')

        if self.config['64bit']:
            retval.append('ENABLE64BIT=Yes')
        else:
            retval.append('ENABLE64BIT=No')

        if "operating_system" in self.config:
            retval.append("OS=%s" % self.config['operating_system'])

        return retval

    def run_make(self, target):
        cmd = ['make', target] + self.query_make_params()
        dirs = self.query_abs_dirs()
        repo_dir = os.path.join(dirs['abs_work_dir'], 'src')
        return self.run_command(cmd, cwd=repo_dir)

    def checkout_sources(self):
        repo = self.config['repo']
        rev = self.config['revision']

        dirs = self.query_abs_dirs()
        repo_dir = os.path.join(dirs['abs_work_dir'], 'src')

        repos = [
            {'vcs': 'gittool', 'repo': repo, 'dest': repo_dir, 'revision': rev},
        ]

        # self.vcs_checkout already retries, so no need to wrap it in
        # self.retry. We set the error_level to ERROR to prevent it going fatal
        # so we can do our own handling here.
        retval = self.vcs_checkout_repos(repos, error_level=ERROR)
        if not retval:
            self.rmtree(repo_dir)
            self.fatal("Automation Error: couldn't clone repo", exit_code=4)

        # Checkout gmp-api
        # TODO: Nothing here updates it yet, or enforces versions!
        if not os.path.exists(os.path.join(repo_dir, 'gmp-api')):
            retval = self.run_make('gmp-bootstrap')
            if retval != 0:
                self.fatal("couldn't bootstrap gmp")
        else:
            self.info("skipping gmp bootstrap - we have it locally")

        # Checkout gtest
        # TODO: Requires svn!
        if not os.path.exists(os.path.join(repo_dir, 'gtest')):
            retval = self.run_make('gtest-bootstrap')
            if retval != 0:
                self.fatal("couldn't bootstrap gtest")
        else:
            self.info("skipping gtest bootstrap - we have it locally")

        return retval

    def build(self):
        retval = self.run_make('plugin')
        if retval != 0:
            self.fatal("couldn't build plugin")

    def upload(self):
        # TODO: Grab libgmpopenh264.so
        pass

    def test(self):
        retval = self.run_make('test')
        if retval != 0:
            self.fatal("test failures")


# main {{{1
if __name__ == '__main__':
    myScript = OpenH264Build()
    myScript.run_and_exit()
