#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import MakefileErrorList
from mozharness.base.script import BaseScript
from mozharness.base.vcs.vcsbase import VCSMixin
from mozharness.mozilla.buildbot import BuildbotMixin
from mozharness.mozilla.mock import MockMixin
from mozharness.mozilla.tooltool import TooltoolMixin

SUCCESS, WARNINGS, FAILURE, EXCEPTION = xrange(4)


class SpidermonkeyBuild(MockMixin, BaseScript, VCSMixin, BuildbotMixin, TooltoolMixin):
    config_options = [
        [["--repo"], {
            "dest": "repo",
            "help": "which gecko repo to get spidermonkey from",
        }],
        [["--revision"], {
            "dest": "revision",
        }],
        [["--branch"], {
            "dest": "branch",
        }],
        [["--vcs-share-base"], {
            "dest": "vcs_share_base",
            "help": "base directory for shared repositories",
        }],
        [["-j"], {
            "dest": "concurrency",
            "type": int,
            "default": 4,
            "help": "number of simultaneous jobs used while building the shell " +
                    "(currently ignored for the analyzed build",
        }],
    ]

    def __init__(self):
        BaseScript.__init__(self,
                            config_options=self.config_options,
                            # other stuff
                            all_actions=[
                                'setup-mock',
                                'reuse-mock',
                                'checkout-tools',

                                # First, build an optimized JS shell for running the analysis
                                'checkout-source',
                                'clobber-shell',
                                'configure-shell',
                                'build-shell',

                                # Next, build a tree with the analysis plugin
                                # active. Note that we are using the same
                                # checkout for the JS shell build and the build
                                # of the source to be analyzed, which is a
                                # little unnecessary (no need to rebuild the JS
                                # shell all the time). (Different objdir,
                                # though.)
                                'clobber-analysis',
                                'setup-analysis',
                                'run-analysis',
                            ],
                            default_actions=[
                                #'reuse-mock',
                                'setup-mock',
                                'checkout-tools',
                                'checkout-source',
                                'clobber-shell',
                                'configure-shell',
                                'build-shell',
                                'clobber-analysis',
                                'setup-analysis',
                                'run-analysis'
                            ],
                            config={
                                'default_vcs': 'hgtool',
                                'vcs_share_base': os.environ.get('HG_SHARE_BASE_DIR'),
                                'ccache': True,
                                'buildbot_json_path': os.environ.get('PROPERTIES_FILE'),
                                'tooltool_servers': None,
                                'tools_repo': 'http://hg.mozilla.org/build/tools',
                            },
                            )

        self.nonmock_env = self.query_env()
        self.env = self.nonmock_env

    def _pre_config_lock(self, rw_config):
        super(SpidermonkeyBuild, self)._pre_config_lock(rw_config)

        if self.buildbot_config is None:
            self.info("Reading buildbot build properties...")
            self.read_buildbot_config()

        self.mock_env = self.query_env(replace_dict=self.config['mock_env_replacements'],
                                       partial_env=self.config['mock_env'])

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = BaseScript.query_abs_dirs(self)

        dirs = {
            'shell-objdir': os.path.join(abs_dirs['abs_work_dir'], self.config['shell-objdir']),
            'mozharness_scriptdir': os.path.abspath(os.path.dirname(__file__))
        }

        abs_dirs.update(dirs)
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def query_repo(self):
        if self.buildbot_config and 'properties' in self.buildbot_config:
            return self.config['hgurl'] + self.buildbot_config['properties']['repo_path']
        else:
            return self.config['repo']

    def query_revision(self):
        if 'revision' in self.buildbot_properties:
            return self.buildbot_properties['revision']

        if self.buildbot_config and 'sourcestamp' in self.buildbot_config:
            return self.buildbot_config['sourcestamp']['revision']

        return None

    def enable_mock(self):
        self.env = self.mock_env
        super(SpidermonkeyBuild, self).enable_mock()

    def disable_mock(self):
        self.env = self.nonmock_env
        super(SpidermonkeyBuild, self).disable_mock()

    # Actions {{{2
    def setup_mock(self):
        MockMixin.setup_mock(self)
        self.enable_mock()

    def reuse_mock(self):
        """Reuse a mock environment without waiting for it to
        reinitialize."""
        self.enable_mock()
        self.done_mock_setup = True

    def checkout_tools(self):
        rev = self.vcs_checkout(
            vcs='hg',  # Don't have hgtool.py yet
            repo=self.config['tools_repo'],
            clean=False,
        )
        self.set_buildbot_property("tools_revision", rev, write_to_file=True)

    def checkout_shell(self):
        dirs = self.query_abs_dirs()
        dest = os.path.join(dirs['abs_work_dir'], 'source')

        # Pre-create the directory to appease the share extension
        if not os.path.exists(dest):
            self.mkdir_p(dest)

        rev = self.vcs_checkout(
            repo=self.query_repo(),
            dest=dest,
            revision=self.query_revision(),
            branch=self.config.get('branch'),
            clean=True,
        )
        self.set_buildbot_property('source_revision', rev, write_to_file=True)

    def clobber_shell(self):
        dirs = self.query_abs_dirs()
        self.rmtree(dirs['shell-objdir'])

    def configure_shell(self):
        dirs = self.query_abs_dirs()

        if not os.path.exists(dirs['shell-objdir']):
            self.mkdir_p(dirs['shell-objdir'])

        rc = self.run_command(['autoconf-2.13'],
                              cwd=dirs['abs_work_dir'] + '/source/js/src',
                              env=self.env,
                              error_list=MakefileErrorList)
        if rc != 0:
            self.fatal("autoconf failed, can't continue.", exit_code=FAILURE)

        rc = self.run_command(['../source/js/src/configure',
                               '--enable-optimize',
                               '--disable-debug',
                               '--enable-ctypes',
                               '--with-system-nspr',
                               '--without-intl-api'],
                              cwd=dirs['shell-objdir'],
                              env=self.env,
                              error_list=MakefileErrorList)
        if rc != 0:
            self.fatal("Configure failed, can't continue.", exit_code=FAILURE)

    def build_shell(self):
        dirs = self.query_abs_dirs()

        rc = self.run_command(['make', '-j', str(self.config['concurrency'])],
                              cwd=dirs['shell-objdir'],
                              env=self.env,
                              error_list=MakefileErrorList)
        if rc != 0:
            self.fatal("Build failed, can't continue.", exit_code=FAILURE)

    def clobber_analysis(self):
        dirs = self.query_abs_dirs()
        analysis_dir = os.path.join(dirs['abs_work_dir'], self.config['analysis-dir'])
        self.rmtree(analysis_dir)

    def setup_analysis(self):
        dirs = self.query_abs_dirs()
        analysis_dir = os.path.join(dirs['abs_work_dir'], self.config['analysis-dir'])

        if not os.path.exists(analysis_dir):
            self.mkdir_p(analysis_dir)

        values = {'js': os.path.join(os.path.join(dirs['abs_work_dir'], self.config['shell-objdir']), 'js'),
                  'analysis_scriptdir': os.path.join(dirs['abs_work_dir'], 'source/js/src/devtools/rootAnalysis'),
                  'source_objdir': os.path.join(dirs['abs_work_dir'], self.config['source-objdir']),
                  'source': os.path.join(dirs['abs_work_dir'], 'source'),
                  'sixgill': self.config['sixgill'],
                  'sixgill_bin': self.config['sixgill_bin'],
                  }
        defaults = """
js = '%(js)s'
analysis_scriptdir = '%(analysis_scriptdir)s'
objdir = '%(source_objdir)s'
source = '%(source)s'
sixgill = '%(sixgill)s'
sixgill_bin = '%(sixgill_bin)s'
jobs = 2
""" % values

        file(os.path.join(analysis_dir, 'defaults.py'), "w").write(defaults)

        self.copyfile(os.path.join(dirs['mozharness_scriptdir'], 'spidermonkey/build.shell'),
                      os.path.join(analysis_dir, 'build.shell'),
                      copystat=True)

    def run_analysis(self):
        dirs = self.query_abs_dirs()
        analysis_dir = os.path.join(dirs['abs_work_dir'], self.config['analysis-dir'])
        analysis_scriptdir = os.path.join(dirs['abs_work_dir'], 'source/js/src/devtools/rootAnalysis')
        analyzed_objdir = os.path.join(dirs['abs_work_dir'], self.config['source-objdir'])

        # The build for the analysis is always a clobber build,
        # because the analysis needs to see every compile to work
        self.rmtree(analyzed_objdir)

        build_command = os.path.abspath(os.path.join(analysis_dir, "build.shell"))
        rc = self.run_command([self.config['python'], os.path.join(analysis_scriptdir, 'analyze.py'),
                               "--buildcommand=%s" % build_command],
                              cwd=analysis_dir,
                              env=self.env,
                              error_list=MakefileErrorList)
        if rc != 0:
            self.fatal("analysis failed, can't continue.", exit_code=FAILURE)

# main {{{1
if __name__ == '__main__':
    myScript = SpidermonkeyBuild()
    myScript.run_and_exit()
