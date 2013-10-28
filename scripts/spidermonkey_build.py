#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
from datetime import datetime
from functools import wraps

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import MakefileErrorList
from mozharness.base.script import BaseScript
from mozharness.base.transfer import TransferMixin
from mozharness.base.vcs.vcsbase import VCSMixin
from mozharness.mozilla.buildbot import BuildbotMixin
from mozharness.mozilla.mock import MockMixin
from mozharness.mozilla.tooltool import TooltoolMixin

SUCCESS, WARNINGS, FAILURE, EXCEPTION = xrange(4)


def requires(*queries):
    def make_wrapper(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            for query in queries:
                val = query(self)
                assert (val is not None and "None" not in str(val)), "invalid " + query.__name__
            return f(self, *args, **kwargs)
        return wrapper
    return make_wrapper


nuisance_env_vars = ['TERMCAP', 'LS_COLORS', 'PWD', '_']


class SpidermonkeyBuild(MockMixin, BaseScript, VCSMixin, BuildbotMixin, TooltoolMixin, TransferMixin):
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
                                'collect-analysis-output',
                                'upload-analysis',
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
                                'run-analysis',
                                'collect-analysis-output',
                                'upload-analysis',
                            ],
                            config={
                                'default_vcs': 'hgtool',
                                'vcs_share_base': os.environ.get('HG_SHARE_BASE_DIR'),
                                'ccache': True,
                                'buildbot_json_path': os.environ.get('PROPERTIES_FILE'),
                                'tooltool_servers': None,
                                'tools_repo': 'http://hg.mozilla.org/build/tools',

                                'upload_ssh_server': None,
                                'upload_remote_basepath': None,
                                'enable_try_uploads': True,
                            },
        )

        self.nonmock_env = self.query_env(purge_env=nuisance_env_vars)
        self.env = self.nonmock_env

        self.buildtime = None

    def _pre_config_lock(self, rw_config):
        super(SpidermonkeyBuild, self)._pre_config_lock(rw_config)

        if self.buildbot_config is None:
            self.info("Reading buildbot build properties...")
            self.read_buildbot_config()

        if self.buildbot_config:
            bb_props = [('mock_target', 'mock_target'),
                        ('base_bundle_urls', 'hgtool_base_bundle_urls'),
                        ('base_mirror_urls', 'hgtool_base_mirror_urls'),
                        ('hgurl', 'hgurl'),
                        ]
            buildbot_props = self.buildbot_config.get('properties', {})
            for bb_prop, cfg_prop in bb_props:
                if not self.config.get(cfg_prop) and buildbot_props.get(bb_prop):
                    self.config[cfg_prop] = buildbot_props[bb_prop]

        self.mock_env = self.query_env(replace_dict=self.config['mock_env_replacements'],
                                       partial_env=self.config['mock_env'],
                                       purge_env=nuisance_env_vars)

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = BaseScript.query_abs_dirs(self)

        abs_work_dir = abs_dirs['abs_work_dir']
        dirs = {
            'shell_objdir':
                os.path.join(abs_work_dir, self.config['shell-objdir']),
            'mozharness_scriptdir':
                os.path.abspath(os.path.dirname(__file__)),
            'abs_analysis_dir':
                os.path.join(abs_work_dir, self.config['analysis-dir']),
            'abs_analyzed_objdir':
                os.path.join(abs_work_dir, self.config['source-objdir']),
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

        # Useful for local testing. In actual use, this would always be None.
        return self.config.get('revision')

    def query_branch(self):
        if self.buildbot_config and 'properties' in self.buildbot_config:
            return self.buildbot_config['properties']['branch']
        elif 'branch' in self.config:
            # Used for locally testing try vs non-try
            return self.config['branch']
        else:
            return os.path.basename(self.query_repo())

    def query_buildtime(self):
        if self.buildtime:
            return self.buildtime
        self.buildtime = datetime.now().strftime("%Y%m%d%H%M%S")
        return self.buildtime

    def query_upload_ssh_server(self):
        if self.buildbot_config and 'properties' in self.buildbot_config:
            return self.buildbot_config['properties']['upload_ssh_server']
        else:
            return self.config['upload_ssh_server']

    def query_upload_ssh_key(self):
        if self.buildbot_config and 'properties' in self.buildbot_config:
            key = self.buildbot_config['properties']['upload_ssh_key']
        else:
            key = self.config['upload_ssh_key']
        if self.mock_enabled and not key.startswith("/"):
            key = "/home/mock_mozilla/.ssh/" + key
        return key

    def query_upload_ssh_user(self):
        if self.buildbot_config and 'properties' in self.buildbot_config:
            return self.buildbot_config['properties']['upload_ssh_user']
        else:
            return self.config['upload_ssh_user']

    def query_product(self):
        if self.buildbot_config and 'properties' in self.buildbot_config:
            return self.buildbot_config['properties']['product']
        else:
            return self.config['product']

    def query_upload_remote_basepath(self):
        if self.config.get('upload_remote_basepath'):
            return self.config['upload_remote_basepath']
        else:
            return "/pub/mozilla.org/{product}".format(
                product=self.query_product(),
            )

    def query_upload_remote_baseuri(self):
        if self.buildbot_config and 'properties' in self.buildbot_config:
            buildprops = self.buildbot_config['properties']
            if 'upload_remote_baseuri' in buildprops:
                return buildprops['upload_remote_baseuri']
        return self.config.get('upload_remote_baseuri')

    def query_target(self):
        if self.buildbot_config and 'properties' in self.buildbot_config:
            return self.buildbot_config['properties']['platform']
        else:
            return self.config.get('target')

    def query_upload_path(self):
        branch = self.query_branch()

        common = {
            'basepath': self.query_upload_remote_basepath(),
            'branch': branch,
            'target': self.query_target(),
        }

        if branch == 'try':
            if not self.config['enable_try_uploads']:
                return None
            try:
                user = self.buildbot_config['sourcestamp']['changes'][0]['who']
            except (KeyError, TypeError):
                user = "unknown"
            return "{basepath}/try-builds/{user}-{rev}/{branch}-{target}".format(
                user=user,
                rev=self.query_revision(),
                **common
            )
        else:
            return "{basepath}/tinderbox-builds/{branch}-{target}/{buildtime}".format(
                buildtime=self.query_buildtime(),
                **common
            )

    def query_do_upload(self):
        if self.query_branch() == 'try':
            return self.config.get('enable_try_uploads')
        return True

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

    @requires(query_repo)
    def checkout_source(self):
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
        self.rmtree(dirs['shell_objdir'])

    def configure_shell(self):
        dirs = self.query_abs_dirs()

        if not os.path.exists(dirs['shell_objdir']):
            self.mkdir_p(dirs['shell_objdir'])

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
                              cwd=dirs['shell_objdir'],
                              env=self.env,
                              error_list=MakefileErrorList)
        if rc != 0:
            self.fatal("Configure failed, can't continue.", exit_code=FAILURE)

    def build_shell(self):
        dirs = self.query_abs_dirs()

        rc = self.run_command(['make', '-j', str(self.config['concurrency']), '-s'],
                              cwd=dirs['shell_objdir'],
                              env=self.env,
                              error_list=MakefileErrorList)
        if rc != 0:
            self.fatal("Build failed, can't continue.", exit_code=FAILURE)

    def clobber_analysis(self):
        dirs = self.query_abs_dirs()
        self.rmtree(dirs['abs_analysis_dir'])
        self.rmtree(dirs['abs_analyzed_objdir'])

    def setup_analysis(self):
        dirs = self.query_abs_dirs()
        analysis_dir = dirs['abs_analysis_dir']

        if not os.path.exists(analysis_dir):
            self.mkdir_p(analysis_dir)

        values = {'js': os.path.join(dirs['shell_objdir'], 'js'),
                  'analysis_scriptdir': os.path.join(dirs['abs_work_dir'], 'source/js/src/devtools/rootAnalysis'),
                  'source_objdir': dirs['abs_analyzed_objdir'],
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

        build_command = self.config['build_command']
        self.copyfile(os.path.join(dirs['mozharness_scriptdir'],
                                   os.path.join('spidermonkey', build_command)),
                      os.path.join(analysis_dir, build_command),
                      copystat=True)

    def run_analysis(self):
        dirs = self.query_abs_dirs()
        analysis_dir = dirs['abs_analysis_dir']
        analysis_scriptdir = os.path.join(dirs['abs_work_dir'], 'source/js/src/devtools/rootAnalysis')

        # The build for the analysis is always a clobber build,
        # because the analysis needs to see every compile to work
        self.rmtree(dirs['abs_analyzed_objdir'])

        build_command = self.config['build_command']
        build_command = os.path.abspath(os.path.join(analysis_dir, build_command))
        rc = self.run_command([self.config['python'], os.path.join(analysis_scriptdir, 'analyze.py'),
                               "--buildcommand=%s" % build_command],
                              cwd=analysis_dir,
                              env=self.env,
                              error_list=MakefileErrorList)
        if rc != 0:
            self.fatal("analysis failed, can't continue.", exit_code=FAILURE)

    def collect_analysis_output(self):
        dirs = self.query_abs_dirs()
        analysis_dir = dirs['abs_analysis_dir']
        upload_dir = dirs['abs_upload_dir']
        self.mkdir_p(upload_dir)
        files = (('rootingHazards.txt',
                  'rooting_hazards',
                  'list of rooting hazards, unsafe references, and extra roots'),
                 ('gcFunctions.txt',
                  'gcFunctions',
                  'list of functions that can gc, and why'),
                 ('gcTypes.txt',
                  'gcTypes',
                  'list of types containing unrooted gc pointers'),
                 ('unnecessary.txt',
                  'extra',
                  'list of extra roots (rooting with no GC function in scope)'),
                 ('refs.txt',
                  'refs',
                  'list of unsafe references to unrooted pointers'),
                 ('hazards.txt',
                  'hazards',
                  'list of just the hazards, together with gcFunction reason for each'))
        for f, short, long in files:
            self.copy_to_upload_dir(os.path.join(analysis_dir, f),
                                    short_desc=short,
                                    long_desc=long,
                                    compress=True)

    @requires(query_upload_path,
              query_upload_ssh_key,
              query_upload_ssh_user,
              query_upload_ssh_server,
              query_upload_remote_baseuri)
    def upload_analysis(self):
        if not self.query_do_upload():
            self.info("Uploads disabled for this build. Skipping...")
            return

        dirs = self.query_abs_dirs()
        upload_path = self.query_upload_path()

        retval = self.rsync_upload_directory(
            dirs['abs_upload_dir'],
            self.query_upload_ssh_key(),
            self.query_upload_ssh_user(),
            self.query_upload_ssh_server(),
            upload_path)

        if retval is not None:
            self.error("failed to upload")
            self.return_code = 2
        else:
            upload_url = "{baseuri}{upload_path}".format(
                baseuri=self.query_upload_remote_baseuri(),
                upload_path=upload_path,
            )

            self.info("Upload successful: %s" % upload_url)

# main {{{1
if __name__ == '__main__':
    myScript = SpidermonkeyBuild()
    myScript.run_and_exit()
