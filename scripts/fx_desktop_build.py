#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""fx_desktop_build.py.

script harness to build nightly firefox within Mozilla's build environment
and developer machines alike

author: Jordan Lund

"""

import sys
import os

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.mozilla.building.buildbase import BUILD_BASE_CONFIG_OPTIONS, \
    BuildingConfig, BuildScript


class FxDesktopBuild(BuildScript, object):
    def __init__(self):
        buildscript_kwargs = {
            'config_options': BUILD_BASE_CONFIG_OPTIONS,
            'all_actions': [
                'clobber',
                'pull',
                'setup-mock',
                'build',
                'generate-build-props',
                'generate-build-stats',
                'symbols',
                'packages',
                'upload',
                'sendchanges',
                'pretty-names',
                'check-l10n',
                'check-test',
                'update',
                'enable-ccache',
            ],
            'require_config_file': True,
            # Default configuration
            'config': {
                "repo_base": "https://hg.mozilla.org",
                "repo_path": "mozilla-central",
                "nightly_build": False,
                "pgo_build": False,
                'is_automation': True,
                # create_snippets will be decided by
                # configs/builds/branch_specifics.py
                # and whether or not this is a nightly build
                "create_snippets": False,
                "create_partial": False,
                # We have "platform_supports_{snippets, partial}" to dictate
                # whether the platform even supports creating_{snippets,
                # partial}. In other words: we create {snippets, partial} if
                # the branch wants it AND the platform supports it. So eg:
                # For nightlies, the 'mozilla-central' branch may set
                # create_snippets to true but if it's a linux asan platform,
                # platform_supports_snippets will be False
                "platform_supports_snippets": True,
                "platform_supports_partials": True,
                'complete_mar_pattern': '*.complete.mar',
                'partial_mar_pattern': '*.partial.*.mar',
                # if nightly and our platform is not an ASAN or Stat Analysis
                # variant, use --release-to-latest in post upload cmd
                'platform_supports_post_upload_to_latest': True,
                'aus2_ssh_key': 'ffxbld_dsa',
                'aus2_user': 'ffxbld',
                'aus2_base_upload_dir': '/opt/aus2/incoming/2/Firefox',
                'balrog_credentials_file': 'oauth.txt',
                'periodic_clobber': 168,  # default anyway but can be overwritten
                # hg tool stuff
                'default_vcs': 'hgtool',
                "repos": [{"repo": "https://hg.mozilla.org/build/tools"}],
                "graph_selector": "/server/collect.cgi",
                'hash_type': 'sha512',
                'tooltool_url': 'http://runtime-binaries.pvt.build.mozilla'
                                '.org/tooltool',
                # only used for make uploadsymbols
                'use_branch_in_symbols_extra_buildid': True,
            },
            'ConfigClass': BuildingConfig,
        }
        super(FxDesktopBuild, self).__init__(**buildscript_kwargs)

    def _pre_config_lock(self, rw_config):
        """grab buildbot props if we are running this in automation"""
        c = self.config
        if c['is_automation']:
            # parse buildbot config and add it to self.config
            self.info("We are running this in buildbot, grab the build props")
            self.read_buildbot_config()
            ###

    # helpers

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        c = self.config
        abs_dirs = super(FxDesktopBuild, self).query_abs_dirs()
        if not c.get('app_ini_path'):
            self.fatal('"app_ini_path" is needed in your config for this '
                       'script.')

        dirs = {
            # BuildFactories in factory.py refer to a 'build' dir on the slave.
            # This contains all the source code/objdir to compile.  However,
            # there is already a build dir in mozharness for every mh run. The
            # 'build' that factory refers to I named: 'source' so
            # there is a seperation in mh.  for example, rather than having
            # '{mozharness_repo}/build/build/', I have '{
            # mozharness_repo}/build/source/'
            'abs_src_dir': os.path.join(abs_dirs['abs_work_dir'],
                                        'source'),
            'abs_obj_dir': os.path.join(abs_dirs['abs_work_dir'],
                                        'source',
                                        self._query_objdir()),
            'abs_tools_dir': os.path.join(abs_dirs['abs_work_dir'], 'tools'),
            'abs_app_ini_path': c['app_ini_path'] % {
                'obj_dir': os.path.join(abs_dirs['abs_work_dir'],
                                        'source',
                                        self._query_objdir())
            },
        }
        abs_dirs.update(dirs)
        self.abs_dirs = abs_dirs
        return self.abs_dirs

        # Actions {{{2
        # read_buildbot_config in BuildingMixin
        # clobber in BuildingMixin -> PurgeMixin
        # if Linux config:
        # reset_mock in BuildingMixing -> MockMixin
        # setup_mock in BuildingMixing (overrides MockMixin.mock_setup)


if __name__ == '__main__':
    fx_desktop_build = FxDesktopBuild()
    fx_desktop_build.run_and_exit()
