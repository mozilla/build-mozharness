#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla.
#
# The Initial Developer of the Original Code is
# the Mozilla Foundation <http://www.mozilla.org/>.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Aki Sasaki <aki@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""Generic VCS support.
"""

import os
import re
import subprocess
from urlparse import urlsplit

import sys
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.dirname(sys.path[0]))))

from mozharness.base.errors import HgErrorList, VCSException
from mozharness.base.log import LogMixin
from mozharness.base.script import BaseScript, ShellMixin, OSMixin
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
                kwargs = repo_dict.copy()
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
