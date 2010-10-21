#!/usr/bin/env python
"""signdebs.py

Usage:
    signdebs.py [args]

TODO: make createRepos and signRepo(s) more standalone for discrete actions
"""

import os
import shutil
import subprocess
import sys
import urllib2
from urllib2 import URLError, HTTPError

# load modules from parent dir
sys.path.insert(1, os.path.join(os.path.dirname(sys.path[0]), "lib"))

from base.config import parseConfigFile
from base.errors import SSHErrorList
from base.script import MercurialScript



# MaemoDebSigner {{{1
class MaemoDebSigner(MercurialScript):
    def __init__(self, require_config_file=True):
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
        MercurialScript.__init__(self, config_options=config_options,
                                 all_actions=['clobber',
                                              'create-repos',
                                              'upload'],
                                 require_config_file=require_config_file)

    def run(self):
        self.clobberRepoDir()
        self.createRepos()
        self.uploadRepos()
        self.summary()

    def _queryDebName(self, deb_name_url=None):
        if self.config.get('deb_name', None):
            return self.config['deb_name']
        if deb_name_url:
            self.info('Getting deb_name from %s' % deb_name_url)
            # TODO belongs in downloadFile or equivalent?
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

    def clobberRepoDir(self):
        if 'clobber' not in self.actions:
            self.actionMessage("Skipping clobber step.")
            return
        self.actionMessage("Clobbering repo dir.")
        c = self.config
        repo_path = os.path.join(c['base_work_dir'], c['work_dir'], c['repo_dir'])
        if os.path.exists(repo_path):
            self.rmtree(repo_path)
        else:
            self.debug("%s doesn't exist." % repo_path)

    def queryLocales(self, platform, platform_config=None):
        locales = self.config.get("locales", None)
        if not locales:
            locales = []
            if not platform_config:
                platform_config = self.config['platform_config']
            pf = platform_config[platform]
            locales_file = self.config['locales_file']
            if "multi_dir_url" in pf:
                locales.append("multi")
            if "en_us_dir_url" in pf:
                locales.append("en-US")
            if "l10n_dir_url" in pf and locales_file:
                """This assumes all locales in the l10n json file
                are applicable. If not, we'll have to parse the json
                for matching platforms.
                """
                if locales_file.endswith(".json"):
                    locales_json = parseConfigFile(locales_file)
                    locales.extend(locales_json.keys())
                else:
                    fh = open(locales_file)
                    additional_locales = fh.read().split()
                    locales.extend(additional_locales)
        return locales

    def _signRepo(self, repo_name, platform):
        c = self.config
        sbox_path = c['sbox_path']
        section = c['section']
        sbox_work_dir = '%s/%s/%s' % (c['work_dir'], c['repo_dir'], repo_name)
        abs_work_dir = '%s/%s' % (c['base_work_dir'], sbox_work_dir)

        # TODO error_list
        error_list = []
        command = "%s -p -d %s apt-ftparchive packages " % (sbox_path, sbox_work_dir)
        command += "dists/%s/%s/binary-armel |" % (platform, section)
        command += "gzip -9c > %s/dists/%s/%s/binary-armel/Packages.gz" % \
                   (abs_work_dir, platform, section)
        status = self.runCommand(command, error_list=error_list)
        if status:
            self.error("Exiting signRepo.")
            return status

        for sub_dir in ("dists/%s/%s/binary-armel" % (platform, section),
                       "dists/%s/%s" % (platform, section),
                       "dists/%s" % platform):
            self.rmtree("%s/%s/Release.gpg" % (abs_work_dir, sub_dir))
            # Create Release file outside of the tree, then move in.
            # TODO error_list
            error_list=[]
            command = "%s -p -d %s/%s " % (sbox_path, sbox_work_dir, sub_dir)
            command += "apt-ftparchive release . > %s/Release.tmp" % abs_work_dir
            if self.runCommand(command, error_list=error_list):
                self.error("Exiting signRepo.")
                return -2
            self.move("%s/Release.tmp" % abs_work_dir,
                      "%s/%s/Release" % (abs_work_dir, sub_dir))

            error_list = [{'regex': 'command not found', 'level': 'error'},
                                {'regex': 'secret key not available', 'level': 'error'},
                               ]
            command = "gpg -abs -o Release.gpg Release"
            if self.runCommand(command, error_list=error_list,
                               cwd='%s/%s' % (abs_work_dir, sub_dir)):
                self.error("Exiting signRepo.")
                return -3
        return 0

    def _createInstallFile(self, file_path, locale, platform):
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
        if self.config['noop']:
            print contents
            return
        fh = open(file_path, 'w')
        print >> fh, contents
        fh.close()
        

    def createRepos(self):
        if 'create-repos' not in self.actions:
            self.actionMessage("Skipping create repo step.")
            return
        self.actionMessage("Creating repos.")
        c = self.config
        platform_config = c['platform_config']
        platforms = self.config.get("platforms", platform_config.keys())

        hg_mobile_repo = c.get('hg_mobile_repo')
        if hg_mobile_repo:
            self.scmCheckout(hg_mobile_repo, dir_name="mobile")
        hg_config_repo = c.get('hg_config_repo')
        if hg_config_repo:
            self.scmCheckout(hg_config_repo, dir_name="configs")

        for platform in platforms:
            """This assumes the same deb name for each locale in a platform.
            """
            self.info("%s" % platform)
            pf = platform_config[platform]
            deb_name = self._queryDebName(deb_name_url=pf['deb_name_url'])
            if not deb_name:
                continue
            locales = self.queryLocales(platform, platform_config=platform_config)
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
                if not self.downloadFile(deb_url, deb_name):
                    self.addSummary("Can't download %s; skipping %s on %s" % \
                                    (deb_url, locale, platform), level="error")
                    self.failures.append('%s_%s' % (platform, locale))
                    continue
                binary_dir = '%s/%s/%s/dists/%s/%s/binary-armel' % \
                             (c['work_dir'], c['repo_dir'], repo_name, platform, c['section'])
                abs_binary_dir = '%s/%s' % (c['base_work_dir'], binary_dir)
                self.mkdir_p(abs_binary_dir)
                self.move(deb_name, abs_binary_dir)

                if self._signRepo(repo_name, platform) != 0:
                    self.addSummary("Can't sign %s; skipping %s on %s" % \
                                    (repo_name, platform, locale), level="error")
                    self.failures.append('%s_%s' % (platform, locale))
                    continue

                self._createInstallFile(os.path.join(c['base_work_dir'],
                                                     c['work_dir'],
                                                     c['repo_dir'],
                                                     repo_name,
                                                     install_file),
                                        locale, platform)

    def uploadRepos(self):
        if 'upload' not in self.actions:
            self.actionMessage("Skipping upload step.")
            return
        self.actionMessage("Uploading repos.")
        c = self.config
        platform_config = c['platform_config']
        platforms = self.config.get("platforms", platform_config.keys())
        for platform in platforms:
            """This assumes the same deb name for each locale in a platform.
            """
            self.info("%s" % platform)
            pf = platform_config[platform]
            locales = self.queryLocales(platform, platform_config=platform_config)
            for locale in locales:
                if '%s_%s' % (platform, locale) not in self.failures:
                    replace_dict = {'locale': locale}
                    install_file = pf['install_file'] % replace_dict
                    repo_name = c['repo_name'] % replace_dict
                    status = self._uploadRepo(os.path.join(c['base_work_dir'],
                                                           c['work_dir'],
                                                           c['repo_dir']),
                                              repo_name, platform, install_file)
                    if status == 0:
                        self.addSummary("Uploaded %s on %s successfully." % \
                                        (locale, platform))

    def _uploadRepo(self, local_repo_dir, repo_name, platform, install_file):
        c = self.config
        remote_repo_path = c['remote_repo_path']
        remote_user = c['remote_user']
        remote_ssh_key = c['remote_ssh_key']
        remote_host = c['remote_host']
        repo_path = os.path.join(local_repo_dir, repo_name, 'dists', platform)
        install_file_path = os.path.join(local_repo_dir, repo_name, install_file)
        num_errors = 0

        if not os.path.isdir(repo_path):
            self.addSummary("Can't upload %s: not a valid repo!" % repo_path,
                            level="error")
            return -1
        if not os.path.exists(install_file_path):
            self.error("uploadRepo: %s doesn't exist!" % install_file_path)

        command = "ssh -i %s %s@%s mkdir -p %s/%s/dists/%s" % \
                  (c['remote_ssh_key'], c['remote_user'], c['remote_host'],
                   c['remote_repo_path'], repo_name, platform)
        num_errors += self.runCommand(command, return_type='num_errors',
                                      error_list=SSHErrorList)

        command = 'rsync --rsh="ssh -i %s" -azv --delete %s %s@%s:%s/%s/dists/%s' % \
                  (remote_ssh_key, os.path.join(repo_path, '.'),
                   remote_user, remote_host, remote_repo_path, repo_name, platform)
        num_errors += self.runCommand(command, return_type='num_errors',
                                      error_list=SSHErrorList)

        command = 'scp -i %s %s %s@%s:%s/%s/' % \
                  (remote_ssh_key, install_file_path,
                   remote_user, remote_host, remote_repo_path, repo_name)
        num_errors += self.runCommand(command, return_type='num_errors',
                                      error_list=SSHErrorList)
        return num_errors



# __main__ {{{1
if __name__ == '__main__':
    debSigner = MaemoDebSigner()
    debSigner.run()
