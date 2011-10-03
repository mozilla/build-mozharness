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
"""signdebs.py

Usage:
    signdebs.py [args]

TODO: make create_repos and sign_repo(s) more standalone for discrete
      actions
"""

import os
import shutil
import subprocess
import sys
import urllib2
from urllib2 import URLError, HTTPError

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.config import parse_config_file
from mozharness.base.errors import SSHErrorList
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.l10n.locales import LocalesMixin



# MaemoDebSigner {{{1
class MaemoDebSigner(LocalesMixin, MercurialScript):
    def __init__(self, require_config_file=True, **kwargs):
        config_options = [[
         ["--locale",],
         {"action": "extend",
          "dest": "locales",
          "type": "string",
          "help": "Specify the locale(s) to repack"
         }
        ],[
         ["--platform",],
         {"action": "extend",
          "dest": "platforms",
          "type": "string",
          "help": "Specify the platform(s) to repack"
         }
        ],[
         ["--deb_name",],
         {"action": "store",
          "dest": "deb_name",
          "type": "string",
          "help": "Specify the name of the deb"
         }
        ]]
        self.failures = []
        LocalesMixin.__init__(self)
        MercurialScript.__init__(self, config_options=config_options,
                                 all_actions=['clobber',
                                              'create-repos',
                                              'upload'],
                                 require_config_file=require_config_file)

    def _query_deb_name(self, deb_name_url=None):
        if self.config.get('deb_name', None):
            return self.config['deb_name']
        if deb_name_url:
            self.info('Getting deb_name from %s' % deb_name_url)
            # TODO belongs in download_file or equivalent?
            try:
                ul = urllib2.build_opener()
                fh = ul.open(deb_name_url)
                deb_name = fh.read().rstrip()
                self.debug('Deb name is %s' % deb_name)
                return deb_name
            except HTTPError, e:
                self.error("HTTP Error: %s %s" % (e.code, deb_name_url))
            except URLError, e:
                self.error("URL Error: %s %s" % (e.code, deb_name_url))

    def clobber(self):
        c = self.config
        repo_path = os.path.join(c['base_work_dir'], c['work_dir'], c['repo_dir'])
        if os.path.exists(repo_path):
            self.rmtree(repo_path)
        else:
            self.debug("%s doesn't exist." % repo_path)

    def query_locales(self):
        if self.locales:
            return self.locales
        c = self.config
        locales = c.get("locales", None)
        if not locales:
            locales = []
            if c.get("locales", True):
                locales = super(MaemoDebSigner, self).query_locales()
            if c.get("multi_locale", True):
                locales = ["multi"] + locales
            locales = ["en-US"] + locales
        self.locales = locales
        return locales

    def _sign_repo(self, repo_name, platform):
        c = self.config
        sbox_path = c['sbox_path']
        section = c['section']
        sbox_work_dir = '%s/%s/%s' % (c['work_dir'], c['repo_dir'], repo_name)
        abs_work_dir = '%s/%s' % (c['base_work_dir'], sbox_work_dir)

        # TODO error_list
        error_list = []
        command = "%s -d %s apt-ftparchive packages " % (sbox_path, sbox_work_dir)
        command += "dists/%s/%s/binary-armel |" % (platform, section)
        command += "gzip -9c > %s/dists/%s/%s/binary-armel/Packages.gz" % \
                   (abs_work_dir, platform, section)
        status = self.run_command(command, error_list=error_list)
        if status:
            self.error("Exiting sign_repo.")
            return status

        for sub_dir in ("dists/%s/%s/binary-armel" % (platform, section),
                       "dists/%s/%s" % (platform, section),
                       "dists/%s" % platform):
            self.rmtree("%s/%s/Release.gpg" % (abs_work_dir, sub_dir))
            # Create Release file outside of the tree, then move in.
            # TODO error_list
            error_list=[]
            command = "%s -d %s/%s " % (sbox_path, sbox_work_dir, sub_dir)
            command += "apt-ftparchive release . > %s/Release.tmp" % abs_work_dir
            if self.run_command(command, error_list=error_list):
                self.error("Exiting sign_repo.")
                return -2
            self.move("%s/Release.tmp" % abs_work_dir,
                      "%s/%s/Release" % (abs_work_dir, sub_dir))

            error_list = [{'regex': 'command not found', 'level': 'error'},
                                {'regex': 'secret key not available', 'level': 'error'},
                               ]
            command = "gpg -abs -o Release.gpg Release"
            if self.run_command(command, error_list=error_list,
                                cwd='%s/%s' % (abs_work_dir, sub_dir)):
                self.error("Exiting sign_repo.")
                return -3
        return 0

    def _create_install_file(self, file_path, locale, platform):
        c = self.config
        platform_config = c['platform_config']
        pf = platform_config[platform]
        replace_dict = {'locale': locale,
                       'long_catalog_name': pf['long_catalog_name'],
                       'package_name': c['package_name'],
                       'platform': platform,
                       'section': c['section'],
                       'short_catalog_name': pf['short_catalog_name'],
                      }
        repo_name = c['repo_name'] % replace_dict
        replace_dict['repo_url'] = '%s/%s' % (c['base_repo_url'], repo_name)
        contents = """[install]
repo_deb_3 = deb %(repo_url)s %(platform)s %(section)s
catalogues = %(short_catalog_name)s
package = %(package_name)s

[fennec]
name =     Mozilla %(long_catalog_name)s %(locale)s Catalog
uri = %(repo_url)s
dist = %(platform)s
components = %(section)s
""" % replace_dict
        self.info("Writing install file to %s" % file_path)
        if self.config.get('noop'):
            print contents
            return
        fh = open(file_path, 'w')
        fh.write("%s\n" % contents)
        fh.close()


    def create_repos(self):
        c = self.config
        platform_config = c['platform_config']
        platforms = c.get("platforms", platform_config.keys())
        abs_work_dir = os.path.join(c['base_work_dir'], c['work_dir'])
        self.mkdir_p(abs_work_dir)

        self.vcs_checkout_repos(c['hg_repos'])

        for platform in platforms:
            """This assumes the same deb name for each locale in a platform.
            """
            self.info("%s" % platform)
            pf = platform_config[platform]
            deb_name = self._query_deb_name(deb_name_url=pf['deb_name_url'])
            if not deb_name:
                continue
            locales = self.query_locales()
            for locale in locales:
                replace_dict = {'locale': locale}
                install_file = pf['install_file'] % replace_dict
                repo_name = c['repo_name'] % replace_dict
                deb_url = ''
                if locale == 'multi':
                    deb_url = pf['multi_dir_url']
                elif locale == 'en-US':
                    deb_url = pf['en_us_dir_url']
                else:
                    deb_url = '%s/%s' % (pf['l10n_dir_url'], locale)
                deb_url += '/%s' % deb_name
                self.debug(deb_url)
                if not self.download_file(deb_url, deb_name):
                    self.add_summary("Can't download %s; skipping %s on %s" % \
                                     (deb_url, locale, platform),
                                     level="error")
                    self.failures.append('%s_%s' % (platform, locale))
                    continue
                binary_dir = '%s/%s/%s/dists/%s/%s/binary-armel' % \
                             (c['work_dir'], c['repo_dir'], repo_name,
                              platform, c['section'])
                abs_binary_dir = '%s/%s' % (c['base_work_dir'], binary_dir)
                self.mkdir_p(abs_binary_dir)
                self.move(deb_name, abs_binary_dir)

                if self._sign_repo(repo_name, platform) != 0:
                    self.add_summary("Can't sign %s; skipping %s on %s" % \
                                     (repo_name, platform, locale),
                                     level="error")
                    self.failures.append('%s_%s' % (platform, locale))
                    continue

                self._create_install_file(os.path.join(c['base_work_dir'],
                                                       c['work_dir'],
                                                       c['repo_dir'],
                                                       repo_name,
                                                       install_file),
                                          locale, platform)

    def upload(self):
        c = self.config
        platform_config = c['platform_config']
        platforms = self.config.get("platforms", platform_config.keys())
        for platform in platforms:
            """This assumes the same deb name for each locale in a platform.
            """
            self.info("%s" % platform)
            pf = platform_config[platform]
            locales = self.query_locales()
            for locale in locales:
                if '%s_%s' % (platform, locale) not in self.failures:
                    replace_dict = {'locale': locale}
                    install_file = pf['install_file'] % replace_dict
                    repo_name = c['repo_name'] % replace_dict
                    status = self._upload_repo(os.path.join(c['base_work_dir'],
                                                            c['work_dir'],
                                                            c['repo_dir']),
                                               repo_name, platform, install_file)
                    if status == 0:
                        self.add_summary("Uploaded %s on %s successfully." % \
                                         (locale, platform))

    def _upload_repo(self, local_repo_dir, repo_name, platform, install_file):
        c = self.config
        remote_repo_path = c['remote_repo_path']
        remote_user = c['remote_user']
        remote_ssh_key = c['remote_ssh_key']
        remote_host = c['remote_host']
        repo_path = os.path.join(local_repo_dir, repo_name, 'dists', platform)
        install_file_path = os.path.join(local_repo_dir, repo_name, install_file)
        num_errors = 0

        if not os.path.isdir(repo_path):
            self.add_summary("Can't upload %s: not a valid repo!" % repo_path,
                            level="error")
            return -1
        if not os.path.exists(install_file_path):
            self.error("uploadRepo: %s doesn't exist!" % install_file_path)

        command = "ssh -i %s %s@%s mkdir -p %s/%s/dists/%s" % \
                  (c['remote_ssh_key'], c['remote_user'], c['remote_host'],
                   c['remote_repo_path'], repo_name, platform)
        num_errors += self.run_command(command, return_type='num_errors',
                                       error_list=SSHErrorList)

        command = 'rsync --rsh="ssh -i %s" -azv --delete %s %s@%s:%s/%s/dists/%s' % \
                  (remote_ssh_key, os.path.join(repo_path, '.'),
                   remote_user, remote_host, remote_repo_path, repo_name, platform)
        num_errors += self.run_command(command, return_type='num_errors',
                                       error_list=SSHErrorList)

        command = 'scp -i %s %s %s@%s:%s/%s/' % \
                  (remote_ssh_key, install_file_path,
                   remote_user, remote_host, remote_repo_path, repo_name)
        num_errors += self.run_command(command, return_type='num_errors',
                                       error_list=SSHErrorList)
        return num_errors



# __main__ {{{1
if __name__ == '__main__':
    debSigner = MaemoDebSigner()
    debSigner.run()
