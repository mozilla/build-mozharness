#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.script import BaseScript
from mozharness.mozilla.mock import MockMixin
from mozharness.base.vcs.vcsbase import VCSMixin
from mozharness.mozilla.buildbot import BuildbotMixin

SUCCESS, WARNINGS, FAILURE, EXCEPTION = xrange(4)

class ServoBuild(MockMixin, BaseScript, VCSMixin, BuildbotMixin):
    config_options = [
        [["--repo"], {
            "dest": "repo",
            "help": "which repo to get servo from",
        }],
        [["--revision"], {
            "dest": "revision",
        }],
        [["--branch"], {
            "dest": "branch",
        }],
        [["--no-backup-rust"], {
            "dest": "backup_rust",
            "action": "store_false",
            "help": "don't backup rust before clobbering",
        }],
        [["--vcs-share-base"], {
            "dest": "vcs_share_base",
            "help": "base directory for shared repositories",
        }],
        [["-j"], {
            "dest": "concurrency",
            "type": int,
        }],
    ]
    def __init__(self):
        BaseScript.__init__(self,
                            config_options=self.config_options,
                            # other stuff
                            all_actions=[
                                'setup-mock',
                                'checkout-servo',
                                'clobber-obj',
                                'configure',
                                'build',
                                'check',
                            ],
                            default_actions=[
                                'checkout-servo',
                                'clobber-obj',
                                'configure',
                                'build',
                                'check',
                            ],
                            config={
                                'default_vcs': 'gittool',
                                'backup_rust': True,
                                'concurrency': 1,
                            },
                            )

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = BaseScript.query_abs_dirs(self)

        dirs = {
            'objdir': os.path.join(abs_dirs['abs_work_dir'], 'objdir'),
        }

        abs_dirs.update(dirs)
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    # Actions {{{2
    def setup_mock(self):
        MockMixin.setup_mock(self)
        self.enable_mock()

    def checkout_servo(self):
        dirs = self.query_abs_dirs()

        rev = self.vcs_checkout(
            repo=self.config.get('repo'),
            dest=dirs['abs_work_dir'],
            revision=self.config.get('revision'),
            branch=self.config.get('branch'),
            clean=True,
        )
        self.set_buildbot_property('got_revision', rev, write_to_file=True)

    def clobber_obj(self):
        dirs = self.query_abs_dirs()

        if self.config.get('backup_rust') and os.path.exists(dirs['objdir']):
            self.run_command(['make', 'backup-rust'], cwd=dirs['objdir'],
                             halt_on_failure=True)
        self.rmtree(dirs['objdir'])

    def configure(self):
        dirs = self.query_abs_dirs()

        if not os.path.exists(dirs['objdir']):
            self.mkdir_p(dirs['objdir'])
        rc = self.run_command(['../configure'], cwd=dirs['objdir'])
        if rc != 0:
            self.fatal("Configure failed, can't continue.", exit_code=FAILURE)

    def build(self):
        dirs = self.query_abs_dirs()

        # If rust was backed up, we need to restore it before building,
        # otherwise it will get rebuilt from scratch.
        if self.config.get('backup_rust'):
            self.run_command(['make', 'restore-rust'], cwd=dirs['objdir'])

        rc = self.run_command(['make', '-j', str(self.config['concurrency'])], cwd=dirs['objdir'])
        if rc != 0:
            self.fatal("Build failed, can't continue.", exit_code=FAILURE)

    def check(self):
        dirs = self.query_abs_dirs()

        rc = self.run_command(['make', 'check'], cwd=dirs['objdir'])
        if rc != 0:
            self.fatal("Tests failed.", exit_code=WARNINGS)


# main {{{1
if __name__ == '__main__':
    myScript = ServoBuild()
    myScript.run()
