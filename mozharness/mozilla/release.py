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
"""release.py

"""

import os

from mozharness.base.config import parse_config_file



# SignAndroid {{{1
class ReleaseMixin():
    release_config = {}

    def query_release_config(self):
        if self.release_config:
            return self.release_config
        c = self.config
        dirs = self.query_abs_dirs()
        if c.get("release_config_file"):
            self.info("Getting release config from %s..." % c["release_config_file"])
            rc = None
            try:
                rc = parse_config_file(
                    os.path.join(dirs['abs_work_dir'],
                                 c["release_config_file"]),
                    config_dict_name="releaseConfig"
                )
            except IOError:
                self.fatal("Release config file %s not found!" % c["release_config_file"])
            except RuntimeError:
                self.fatal("Invalid release config file %s!" % c["release_config_file"])
            self.release_config['version'] = rc['version']
            self.release_config['buildnum'] = rc['buildNumber']
            self.release_config['old_version'] = rc['oldVersion']
            self.release_config['old_buildnum'] = rc['oldBuildNumber']
            self.release_config['ftp_server'] = rc['stagingServer']
            self.release_config['ftp_user'] = c.get('ftp_user', rc['hgUsername'])
            self.release_config['ftp_ssh_key'] = c.get('ftp_ssh_key', rc['hgSshKey'])
            self.release_config['aus_server'] = rc['ausHost']
            self.release_config['aus_user'] = rc['ausUser']
            self.release_config['aus_ssh_key'] = c.get('aus_ssh_key', '~/.ssh/%s' % rc['ausSshKey'])
        else:
            self.info("No release config file; using default config.")
            for key in ('version', 'buildnum', 'old_version', 'old_buildnum',
                        'ftp_server', 'ftp_user', 'ftp_ssh_key',
                        'aus_server', 'aus_user', 'aus_ssh_key',):
                self.release_config[key] = c[key]
        self.info("Release config:\n%s" % self.release_config)
        return self.release_config
