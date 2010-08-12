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
sys.path[0] = os.path.dirname(sys.path[0])

import log
reload(log)
from log import SimpleFileLogger, BasicFunctions, SSHErrorRegexList, HgErrorRegexList

import config
reload(config)
from config import SimpleConfig



# MaemoDebSigner {{{1
class MaemoDebSigner(SimpleConfig):
    def __init__(self, require_config_file=True):
        """I wanted to inherit BasicFunctions in SimpleFileLogger but
        that ends up not carrying down to this object since SimpleConfig
        doesn't inherit the logger, just has a self.logObj.
        """
        config_options = [[
         ["--locale",],
         {"action": "append_split",
          "dest": "locales",
          "type": "string",
          "help": "Specify the locale(s) to repack"
         }
        ],[
         ["--platform",],
         {"action": "append_split",
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
        SimpleConfig.__init__(self, config_options=config_options,
                              all_actions=['clobber', 'create-repos',
                                           'upload'],
                              require_config_file=require_config_file)
        self.failures = []

    def run(self):
        self.clobberRepoDir()
        self.createRepos()
        self.uploadRepos()
        if self.failures:
            self.error("%s failures: %s" % (self.__class__.__name__,
                                            self.failures))

    def _queryDebName(self, deb_name_url=None):
        deb_name = self.queryVar('deb_name')
        if deb_name:
            return deb_name
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
        if not self.queryAction('clobber'):
            self.info("Skipping clobber step.")
            return
        self.info("Clobbering repo dir.")
        base_work_dir = self.queryVar("base_work_dir")
        work_dir = self.queryVar("work_dir")
        repo_dir = self.queryVar("repo_dir")
        if not work_dir or not base_work_dir or not repo_dir:
            self.fatal("base_work_dir, work_dir, repo_dir need to be set!")
        repo_path = os.path.join(base_work_dir, work_dir, repo_dir)
        if os.path.exists(repo_path):
            self.rmtree(repo_path)
        else:
            self.debug("%s doesn't exist." % repo_path)

    def _queryLocales(self, platform, platform_config=None):
        locales = self.queryVar("locales")
        if not locales:
            locales = []
            if not platform_config:
                platform_config = self.queryVar("platform_config")
            pf = platform_config[platform]
            locales_file = self.queryVar("locales_file")
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
                    locales_json = self.parseConfigFile(locales_file)
                    locales.extend(locales_json.keys())
                else:
                    fh = open(locales_file)
                    additional_locales = fh.read().split()
                    locales.extend(additional_locales)
        return locales

    def _signRepo(self, repo_name, platform):
        base_work_dir = self.queryVar("base_work_dir")
        repo_dir = self.queryVar("repo_dir")
        sbox_path = self.queryVar("sbox_path")
        section = self.queryVar("section")
        work_dir = self.queryVar("work_dir")
        sbox_work_dir = '%s/%s/%s' % (work_dir, repo_dir, repo_name)
        abs_work_dir = '%s/%s' % (base_work_dir, sbox_work_dir)

        # TODO errorRegex
        error_regex_list = []
        command = "%s -p -d %s apt-ftparchive packages " % (sbox_path, sbox_work_dir)
        command += "dists/%s/%s/binary-armel |" % (platform, section)
        command += "gzip -9c > %s/dists/%s/%s/binary-armel/Packages.gz" % \
                   (abs_work_dir, platform, section)
        status = self.runCommand(command, error_regex_list=error_regex_list)
        if status:
            self.error("Exiting signRepo.")
            return status

        for sub_dir in ("dists/%s/%s/binary-armel" % (platform, section),
                       "dists/%s/%s" % (platform, section),
                       "dists/%s" % platform):
            self.rmtree("%s/%s/Release.gpg" % (abs_work_dir, sub_dir))
            # Create Release file outside of the tree, then move in.
            # TODO error_regex_list
            error_regex_list=[]
            command = "%s -p -d %s/%s " % (sbox_path, sbox_work_dir, sub_dir)
            command += "apt-ftparchive release . > %s/Release.tmp" % abs_work_dir
            if self.runCommand(command, error_regex_list=error_regex_list):
                self.error("Exiting signRepo.")
                return -2
            self.move("%s/Release.tmp" % abs_work_dir,
                      "%s/%s/Release" % (abs_work_dir, sub_dir))

            error_regex_list = [{'regex': 'command not found', 'level': 'error'},
                                {'regex': 'secret key not available', 'level': 'error'},
                               ]
            command = "gpg -abs -o Release.gpg Release"
            if self.runCommand(command, error_regex_list=error_regex_list,
                               cwd='%s/%s' % (abs_work_dir, sub_dir)):
                self.error("Exiting signRepo.")
                return -3
        return 0

    def _createInstallFile(self, file_path, locale, platform):
        base_repo_url = self.queryVar("base_repo_url")
        package_name = self.queryVar("package_name")
        platform_config = self.queryVar("platform_config")
        section = self.queryVar("section")
        pf = platform_config[platform]
        replace_dict = {'locale': locale,
                       'long_catalog_name': pf['long_catalog_name'],
                       'package_name': package_name,
                       'platform': platform,
                       'section': section,
                       'short_catalog_name': pf['short_catalog_name'],
                      }
        repo_name = self.queryVar('repo_name') % replace_dict
        replace_dict['repo_url'] = '%s/%s' % (base_repo_url, repo_name)
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
        fh = open(file_path, 'w')
        print >> fh, contents
        fh.close()
        

    def createRepos(self):
        if not self.queryAction('create-repos'):
            self.info("Skipping create repo step.")
            return
        self.info("Creating repos.")
        base_work_dir = self.queryVar("base_work_dir")
        hg_mobile_repo = self.queryVar("hg_mobile_repo")
        hg_config_repo = self.queryVar("hg_config_repo")
        platform_config = self.queryVar("platform_config")
        platforms = self.queryVar("platforms", default=platform_config.keys())
        repo_dir = self.queryVar("repo_dir")
        sbox_path = self.queryVar("sbox_path")
        section = self.queryVar("section")
        work_dir = self.queryVar("work_dir")

        if hg_mobile_repo is not None:
            if not os.path.exists('mobile'):
                self.runCommand("hg clone %s mobile" % hg_mobile_repo,
                                error_regex_list=HgErrorRegexList)
            self.runCommand("hg --cwd mobile pull", error_regex_list=HgErrorRegexList)
            self.runCommand("hg --cwd mobile update -C", error_regex_list=HgErrorRegexList)
        if hg_config_repo is not None:
            if not os.path.exists('configs'):
                self.runCommand("hg clone %s configs" % hg_config_repo,
                                error_regex_list=HgErrorRegexList)
            self.runCommand("hg --cwd configs pull", error_regex_list=HgErrorRegexList)
            self.runCommand("hg --cwd configs update -C", error_regex_list=HgErrorRegexList)

        for platform in platforms:
            """This assumes the same deb name for each locale in a platform.
            """
            self.info("%s" % platform)
            pf = platform_config[platform]
            deb_name = self._queryDebName(deb_name_url=pf['deb_name_url'])
            if not deb_name:
                continue
            locales = self._queryLocales(platform, platform_config=platform_config)
            for locale in locales:
                replace_dict = {'locale': locale}
                install_file = pf['install_file'] % replace_dict
                repo_name = self.queryVar('repo_name') % replace_dict
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
                    self.warn("Skipping %s ..." % locale)
                    continue
                binary_dir = '%s/%s/%s/dists/%s/%s/binary-armel' % \
                             (work_dir, repo_dir, repo_name, platform, section)
                abs_binary_dir = '%s/%s' % (base_work_dir, binary_dir)
                self.mkdir_p(abs_binary_dir)
                self.move(deb_name, abs_binary_dir)

                if self._signRepo(repo_name, platform) != 0:
                    self.error("Skipping %s %s" % (platform, locale))
                    self.failures.append('%s_%s' % (platform, locale))
                    continue

                self._createInstallFile(os.path.join(base_work_dir, work_dir,
                                                    repo_dir, repo_name,
                                                    install_file),
                                       locale, platform)

    def uploadRepos(self):
        if not self.queryAction('upload'):
            self.info("Skipping upload step.")
            return
        self.info("Uploading repos.")
        base_work_dir = self.queryVar("base_work_dir")
        platform_config = self.queryVar("platform_config")
        platforms = self.queryVar("platforms", default=platform_config.keys())
        repo_dir = self.queryVar("repo_dir")
        work_dir = self.queryVar("work_dir")
        for platform in platforms:
            """This assumes the same deb name for each locale in a platform.
            """
            self.info("%s" % platform)
            pf = platform_config[platform]
            locales = self._queryLocales(platform, platform_config=platform_config)
            for locale in locales:
                if '%s_%s' % (platform, locale) not in self.failures:
                    replace_dict = {'locale': locale}
                    install_file = pf['install_file'] % replace_dict
                    repo_name = self.queryVar('repo_name') % replace_dict
                    self._uploadRepo(os.path.join(base_work_dir, work_dir, repo_dir),
                                     repo_name, platform, install_file)

    def _uploadRepo(self, local_repo_dir, repo_name, platform, install_file):
        remote_repo_path = self.queryVar("remote_repo_path")
        remote_user = self.queryVar("remote_user")
        remote_ssh_key = self.queryVar("remote_ssh_key")
        remote_host = self.queryVar("remote_host")
        repo_path = os.path.join(local_repo_dir, repo_name, 'dists', platform)
        install_file_path = os.path.join(local_repo_dir, repo_name, install_file)

        if not os.path.isdir(repo_path):
            self.error("uploadRepo: %s isn't a valid repo!" % repo_path)
            return -1
        if not os.path.exists(install_file_path):
            self.error("uploadRepo: %s doesn't exist!" % install_file_path)

        command = "ssh -i %s %s@%s mkdir -p %s/%s/dists/%s" % \
                  (remote_ssh_key, remote_user, remote_host, remote_repo_path,
                   repo_name, platform)
        self.runCommand(command, error_regex_list=SSHErrorRegexList)

        command = 'rsync --rsh="ssh -i %s" -azv --delete %s %s@%s:%s/%s/dists/%s' % \
                  (remote_ssh_key, os.path.join(repo_path, '.'),
                   remote_user, remote_host, remote_repo_path, repo_name, platform)
        self.runCommand(command, error_regex_list=SSHErrorRegexList)

        command = 'scp -i %s %s %s@%s:%s/%s/' % \
                  (remote_ssh_key, install_file_path,
                   remote_user, remote_host, remote_repo_path, repo_name)
        self.runCommand(command, error_regex_list=SSHErrorRegexList)



# __main__ {{{1
if __name__ == '__main__':
    debSigner = MaemoDebSigner()
    debSigner.run()
