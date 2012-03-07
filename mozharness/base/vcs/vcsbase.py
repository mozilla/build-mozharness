#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Generic VCS support.
"""

from copy import deepcopy
import os

import sys
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.dirname(sys.path[0]))))

from mozharness.base.errors import VCSException
from mozharness.base.script import BaseScript
from mozharness.base.vcs.mercurial import MercurialVCS

# Update this with supported VCS name : VCS object
VCS_DICT = {
    'hg': MercurialVCS,
}

# VCSMixin {{{1
class VCSMixin(object):
    def vcs_checkout(self, vcs=None, **kwargs):
        c = self.config
        if not vcs:
            if c.get('default_vcs'):
                vcs = c['default_vcs']
            else:
                try:
                    vcs = self.default_vcs
                except AttributeError:
                    pass
        vcs_class = VCS_DICT.get(vcs)
        if not vcs_class:
            self.error("Running vcs_checkout with kwargs %s" % str(**kwargs))
            raise VCSException, "No VCS set!"
        # need a better way to do this.
        if 'dest' not in kwargs:
            kwargs['dest'] = os.path.basename(kwargs['repo'])
        if 'vcs_share_base' not in kwargs:
            kwargs['vcs_share_base'] = c.get('vcs_share_base')
        vcs_obj = vcs_class(
         log_obj=self.log_obj,
         config=self.config,
         vcs_config=kwargs,
        )
        got_revision = vcs_obj.ensure_repo_and_revision()
        if got_revision:
            return got_revision
        else:
            raise VCSException, "No got_revision from ensure_repo_and_revision()"

    def vcs_checkout_repos(self, repo_list, parent_dir=None,
                           tag_override=None, **kwargs):
        orig_dir = os.getcwd()
        c = self.config
        if not parent_dir:
            parent_dir = os.path.join(c['base_work_dir'], c['work_dir'])
        self.mkdir_p(parent_dir)
        self.chdir(parent_dir)
        try:
            for repo_dict in repo_list:
                kwargs = deepcopy(repo_dict)
                if tag_override:
                    kwargs['revision'] = tag_override
                self.vcs_checkout(**kwargs)
        finally:
            self.chdir(orig_dir)

class VCSScript(VCSMixin, BaseScript):
    def __init__(self, **kwargs):
        super(VCSScript, self).__init__(**kwargs)

# Specific VCS stubs {{{1
# For ease of use.
# This is here instead of mercurial.py because importing MercurialVCS into
# vcsbase from mercurial, and importing VCSScript into mercurial from
# vcsbase, was giving me issues.
class MercurialScript(VCSScript):
    default_vcs = 'hg'



# __main__ {{{1
if __name__ == '__main__':
    pass
