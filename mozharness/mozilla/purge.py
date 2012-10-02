#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Purge/clobber support
"""

# Figure out where our external_tools are
# These are in a sibling directory to the 'mozharness' module
import os
import mozharness
external_tools_path = os.path.join(
    os.path.abspath(os.path.dirname(os.path.dirname(mozharness.__file__))),
    'external_tools',
)


# PurgeMixin {{{1
# Depends on ShellMixin for self.run_command,
# and BuildbotMixin for self.buildbot_config
class PurgeMixin(object):
    purge_tool = os.path.join(external_tools_path, 'purge_builds.py')

    default_skips = ['info', 'rel-*']
    default_maxage = 14

    def purge_builds(self, basedir=None, min_size=None, skip=None, max_age=None):
        c = self.config
        min_size = min_size or c['purge_minsize']
        max_age = max_age or c.get('purge_maxage') or self.default_maxage
        skip = skip or c.get('purge_skip') or self.default_skips

        if not basedir:
            assert self.buildbot_config
            basedir = os.path.dirname(self.buildbot_config['properties']['basedir'])

        # Add --dry-run if you don't want to do this for realz
        cmd = [self.purge_tool,
               '-s', str(min_size),
               ]

        if max_age:
            cmd.extend(['--max-age', str(max_age)])

        for s in skip:
            cmd.extend(['--not', s])

        cmd.append(basedir)

        # purge_builds.py can also clean up old shared hg repos if we set
        # HG_SHARE_BASE_DIR accordingly
        env = {'PATH': os.environ.get('PATH')}
        share_base = c.get('vcs_share_base', os.environ.get("HG_SHARE_BASE_DIR", None))
        if share_base:
            env['HG_SHARE_BASE_DIR'] = share_base
        retval = self.run_command(cmd, env=env)
        if retval != 0:
            self.fatal("failed to purge builds", exit_code=2)
