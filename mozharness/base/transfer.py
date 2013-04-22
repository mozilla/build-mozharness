#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Generic ways to upload + download files.
"""

import os
import urllib2
try:
    import simplejson as json
    assert json
except ImportError:
    import json

from mozharness.base.errors import SSHErrorList
from mozharness.base.log import ERROR


# TransferMixin {{{1
class TransferMixin(object):
    """
    Generic transfer methods.

    Dependent on BaseScript.
    """
    def rsync_upload_directory(self, local_path, ssh_key, ssh_user,
                               remote_host, remote_path,
                               rsync_options=None,
                               error_level=ERROR,
                               create_remote_directory=True,
                              ):
        """
        Create a remote directory and upload the contents of
        a local directory to it via rsync+ssh.

        Return None on success, not None on failure.
        """
        dirs = self.query_abs_dirs()
        self.info("Uploading the contents of %s to %s:%s" % (local_path, remote_host, remote_path))
        rsync = self.query_exe("rsync")
        ssh = self.query_exe("ssh")
        if rsync_options is None:
            rsync_options = ['-azv']
        if not os.path.isdir(local_path):
            self.log("%s isn't a directory!" % local_path,
                     level=ERROR)
            return -1
        if create_remote_directory:
            mkdir_error_list = [{
                'substr': r'''exists but is not a directory''',
                'level': ERROR
            }] + SSHErrorList
            if self.run_command([ssh, '-oIdentityFile=%s' % ssh_key,
                                 '%s@%s' % (ssh_user, remote_host),
                                 'mkdir', '-p', remote_path],
                                cwd=dirs['abs_work_dir'],
                                return_type='num_errors',
                                error_list=mkdir_error_list):
                self.log("Unable to create remote directory %s:%s!" % (remote_host, remote_path), level=error_level)
                return -2
        if self.run_command([rsync, '-e',
                             '%s -oIdentityFile=%s' % (ssh, ssh_key)
                            ] + rsync_options + ['.',
                             '%s@%s:%s/' % (ssh_user, remote_host, remote_path)],
                            cwd=local_path,
                            return_type='num_errors',
                            error_list=SSHErrorList):
            self.log("Unable to rsync %s to %s:%s!" % (local_path, remote_host, remote_path), level=error_level)
            return -3

    def rsync_download_directory(self, ssh_key, ssh_user, remote_host,
                                 remote_path, local_path,
                                 rsync_options=None,
                                 error_level=ERROR,
                                ):
        """
        Create a remote directory and upload the contents of
        a local directory to it via rsync+ssh.

        Return None on success, not None on failure.
        """
        self.info("Downloading the contents of %s:%s to %s" % (remote_host, remote_path, local_path))
        rsync = self.query_exe("rsync")
        ssh = self.query_exe("ssh")
        if rsync_options is None:
            rsync_options = ['-azv']
        if not os.path.isdir(local_path):
            self.log("%s isn't a directory!" % local_path,
                     level=error_level)
            return -1
        if self.run_command([rsync, '-e',
                             '%s -oIdentityFile=%s' % (ssh, ssh_key)
                            ] + rsync_options + [
                             '%s@%s:%s/' % (ssh_user, remote_host, remote_path),
                             '.'],
                            cwd=local_path,
                            return_type='num_errors',
                            error_list=SSHErrorList):
            self.log("Unable to rsync %s:%s to %s!" % (remote_host, remote_path, local_path), level=error_level)
            return -3

    def load_json_from_url(self, url, timeout=30):
        self.debug("Attempting to download %s; timeout=%i" % (url, timeout))
        r = urllib2.urlopen(url, timeout=timeout)
        j = json.load(r)
        return j
