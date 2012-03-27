#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""sign_android.py

"""
# TODO split out signing and transfers to helper objects so we can do
#      the downloads/signing/uploads in parallel, speeding that up
# TODO retire this script when Android signing-on-demand lands.

from copy import deepcopy
import os
import sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import BaseErrorList
from mozharness.base.log import ERROR, FATAL
from mozharness.base.transfer import TransferMixin
from mozharness.mozilla.release import ReleaseMixin
from mozharness.mozilla.signing import MobileSigningMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.l10n.locales import LocalesMixin

# So far this only references the ftp platform name.
SUPPORTED_PLATFORMS = ["android", "android-xul"]



# SignAndroid {{{1
class SignAndroid(LocalesMixin, ReleaseMixin, MobileSigningMixin,
                  TransferMixin, MercurialScript):
    config_options = [[
     ['--locale',],
     {"action": "extend",
      "dest": "locales",
      "type": "string",
      "help": "Specify the locale(s) to sign and update"
     }
    ],[
     ['--locales-file',],
     {"action": "store",
      "dest": "locales_file",
      "type": "string",
      "help": "Specify a json file to determine which locales to sign and update"
     }
    ],[
     ['--tag-override',],
     {"action": "store",
      "dest": "tag_override",
      "type": "string",
      "help": "Override the tags set for all repos"
     }
    ],[
     ['--platform',],
     {"action": "extend",
      "dest": "platforms",
      "type": "choice",
      "choices": SUPPORTED_PLATFORMS,
      "help": "Specify the platform(s) to sign"
     }
    ],[
     ['--user-repo-override',],
     {"action": "store",
      "dest": "user_repo_override",
      "type": "string",
      "help": "Override the user repo path for all repos"
     }
    ],[
     ['--key-alias',],
     {"action": "store",
      "dest": "key_alias",
      "type": "choice",
      "choices": ['production', 'nightly'],
      "help": "Specify the key alias"
     }
    ],[
     ['--update-platform',],
     {"action": "extend",
      "dest": "update_platforms",
      "type": "choice",
      "choices": SUPPORTED_PLATFORMS,
      "help": "Specify the platform(s) to create update snippets for"
     }
    ],[
     ['--release-config-file',],
     {"action": "store",
      "dest": "release_config_file",
      "type": "string",
      "help": "Specify the release config file to use"
     }
    ],[
     ['--version',],
     {"action": "store",
      "dest": "version",
      "type": "string",
      "help": "Specify the current version"
     }
    ],[
     ['--old-version',],
     {"action": "store",
      "dest": "old_version",
      "type": "string",
      "help": "Specify the version to update from"
     }
    ],[
     ['--buildnum',],
     {"action": "store",
      "dest": "buildnum",
      "type": "int",
      "default": 1,
      "metavar": "INT",
      "help": "Specify the current release build num (e.g. build1, build2)"
     }
    ],[
     ['--old-buildnum',],
     {"action": "store",
      "dest": "old_buildnum",
      "type": "int",
      "default": 1,
      "metavar": "INT",
      "help": "Specify the release build num to update from (e.g. build1, build2)"
     }
    ],[
     ['--keystore',],
     {"action": "store",
      "dest": "keystore",
      "type": "string",
      "help": "Specify the location of the signing keystore"
     }
    ],[
    # XXX this is a bit of a hack.
    # Ideally we'd have fully configured partner repack info with their own
    # actions so they could be handled discretely.
    # However, the ideal long term solution will involve signing-on-demand;
    # this, along with signing support in mobile_partner_repack.py,
    # seems to be an acceptable interim solution.
     ['--with-partner-repacks',],
     {"action": "store_true",
      "dest": "enable_partner_repacks",
      "default": False,
      "help": "Download, sign, and verify partner repacks as well."
     }
    ]]

    def __init__(self, require_config_file=True):
        self.release_config = {}
        LocalesMixin.__init__(self)
        MobileSigningMixin.__init__(self)
        MercurialScript.__init__(self,
            config_options=self.config_options,
            all_actions=[
                "passphrase",
                "clobber",
                "pull",
                "download-unsigned-bits",
                "sign",
                "verify-signatures",
                "upload-signed-bits",
                "create-snippets",
                "upload-snippets",
            ],
            require_config_file=require_config_file
        )

    # Helper methods {{{2
    def query_buildid(self, platform, base_url, buildnum=None, version=None):
        rc = self.query_release_config()
        replace_dict = {
            'buildnum': rc['buildnum'],
            'version': rc['version'],
            'platform': platform,
        }
        if buildnum:
            replace_dict['buildnum'] = buildnum
        if version:
            replace_dict['version'] = version
        url = base_url % replace_dict
        # ghetto retry.
        for count in range (1, 11):
        # TODO stop using curl
            output = self.get_output_from_command(["curl", "--silent", url])
            if output.startswith("buildID="):
                return output.replace("buildID=", "")
            else:
                self.warning("Can't get buildID from %s (try %d)" % (url, count))
        # This will break create-snippets if it isn't set.
        # Might as well fatal().
        self.fatal("Can't get buildID from %s!" % url)

    def add_failure(self, platform, locale, **kwargs):
        s = "%s:%s" % (platform, locale)
        if 'message' in kwargs:
            kwargs['message'] = kwargs['message'] % {'platform': platform, 'locale': locale}
        super(SignAndroid, self).add_failure(s, **kwargs)

    def query_failure(self, platform, locale):
        s = "%s:%s" % (platform, locale)
        return super(SignAndroid, self).query_failure(s)

    # Actions {{{2

    # passphrase() is in AndroidSigningMixin
    # verify_passphrases() is in AndroidSigningMixin
    # postflight_passphrase() is in AndroidSigningMixin

    def pull(self):
        c = self.config
        dirs = self.query_abs_dirs()
        repos = []
        replace_dict = {}
        if c.get("user_repo_override"):
            replace_dict['user_repo_override'] = c['user_repo_override']
            # deepcopy() needed because of self.config lock bug :(
            for repo_dict in deepcopy(c['repos']):
                repo_dict['repo'] = repo_dict['repo'] % replace_dict
                repos.append(repo_dict)
        else:
            repos = c['repos']
        self.vcs_checkout_repos(repos, parent_dir=dirs['abs_work_dir'],
                                tag_override=c.get('tag_override'))

    def download_unsigned_bits(self):
        c = self.config
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        base_url = c['download_base_url'] + '/' + \
                   c['download_unsigned_base_subdir'] + '/' + \
                   c.get('unsigned_apk_base_name', 'gecko-unsigned-unaligned.apk')
        replace_dict = {
            'buildnum': rc['buildnum'],
            'version': rc['version'],
        }
        success_count = total_count = 0
        for platform in c['platforms']:
            replace_dict['platform'] = platform
            for locale in locales:
                replace_dict['locale'] = locale
                url = base_url % replace_dict
                parent_dir = '%s/unsigned/%s/%s' % (dirs['abs_work_dir'],
                                           platform, locale)
                file_path = '%s/gecko.ap_' % parent_dir
                self.mkdir_p(parent_dir)
                total_count += 1
                if not self.download_file(url, file_path):
                    self.add_failure(platform, locale,
                                     message="Unable to download %(platform)s:%(locale)s unsigned apk!")
                else:
                    success_count += 1
        self.summarize_success_count(success_count, total_count,
                                     message="Downloaded %d of %d unsigned apks successfully.")
        if c['enable_partner_repacks']:
            self.info("Downloading partner-repacks")
            if replace_dict.get('platform'):
                del(replace_dict['platform'])
            remote_dir = c['ftp_upload_base_dir'] % replace_dict + '/unsigned/partner-repacks'
            local_dir = os.path.join(dirs['abs_work_dir'], 'unsigned', 'partner-repacks')
            self.mkdir_p(local_dir)
            if self.rsync_download_directory(rc['ftp_ssh_key'], rc['ftp_user'],
                                             rc['ftp_server'], remote_dir,
                                             local_dir):
                self.add_summary("Unable to download partner repacks!", level=ERROR)
                self.rmtree(local_dir)

    def preflight_sign(self):
        if 'passphrase' not in self.actions:
            self.passphrase()
            self.verify_passphrases()

    def sign(self):
        c = self.config
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        success_count = total_count = 0
        for platform in c['platforms']:
            for locale in locales:
                if self.query_failure(platform, locale):
                    self.warning("%s:%s had previous issues; skipping!" % (platform, locale))
                    continue
                unsigned_path = '%s/unsigned/%s/%s/gecko.ap_' % (dirs['abs_work_dir'], platform, locale)
                signed_dir = '%s/signed/%s/%s' % (dirs['abs_work_dir'], platform, locale)
                signed_file_name = c['apk_base_name'] % {'version': rc['version'],
                                                         'locale': locale}
                signed_path = "%s/%s" % (signed_dir, signed_file_name)
                total_count += 1
                self.info("Signing %s %s." % (platform, locale))
                if not os.path.exists(unsigned_path):
                    self.error("Missing apk %s!" % unsigned_path)
                    continue
                if self.sign_apk(unsigned_path, c['keystore'],
                                 self.store_passphrase, self.key_passphrase,
                                 c['key_alias']) != 0:
                    self.add_summary("Unable to sign %s:%s apk!" % (platform, locale),
                                     level=FATAL)
                else:
                    self.mkdir_p(signed_dir)
                    if self.align_apk(unsigned_path, signed_path):
                        self.add_failure(platform, locale,
                                         message="Unable to align %(platform)s:%(locale)s apk!")
                        self.rmtree(signed_dir)
                    else:
                        success_count += 1
        self.summarize_success_count(success_count, total_count,
                                     message="Signed %d of %d apks successfully.")
        if c['enable_partner_repacks']:
            total_count = success_count = 0
            self.info("Signing partner repacks.")
            for partner in c.get("partners", []):
                for platform in c.get("partner_platforms", []):
                    for locale in locales:
                        file_name = c['apk_base_name'] % {'version': rc['version'],
                                                          'locale': locale}
                        unsigned_path = '%s/unsigned/partner-repacks/%s/%s/%s/%s' % (dirs['abs_work_dir'], partner, platform, locale, file_name)
                        signed_dir = '%s/signed/partner-repacks/%s/%s/%s' % (dirs['abs_work_dir'], partner, platform, locale)
                        signed_path = '%s/%s' % (signed_dir, file_name)
                        total_count += 1
                        self.info("Signing %s %s %s." % (partner, platform, locale))
                        if not os.path.exists(unsigned_path):
                            self.warning("%s doesn't exist; skipping." % unsigned_path)
                            continue
                        if self.sign_apk(unsigned_path, c['keystore'],
                                         self.store_passphrase, self.key_passphrase,
                                         c['key_alias']) != 0:
                            self.add_summary("Unable to sign %s %s:%s apk!" % (partner, platform, locale),
                                             level=ERROR)
                            continue
                        else:
                            self.mkdir_p(signed_dir)
                            if self.align_apk(unsigned_path, signed_path):
                                self.add_summary("Unable to align %s %s:%s apk!" % (partner, platform, locale))
                                self.rmtree(signed_dir)
                            else:
                                success_count += 1
            self.summarize_success_count(success_count, total_count,
                                         message="Signed %d of %d partner apks successfully.")

    def verify_signatures(self):
        c = self.config
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        env = self.query_env(partial_env=c.get("env"))
        for platform in c['platforms']:
            for locale in locales:
                if self.query_failure(platform, locale):
                    self.warning("%s:%s had previous issues; skipping!" % (platform, locale))
                    continue
                signed_path = 'signed/%s/%s/%s' % (platform, locale,
                    c['apk_base_name'] % {'version': rc['version'],
                                          'locale': locale})
                if not os.path.exists(os.path.join(dirs['abs_work_dir'],
                                                   signed_path)):
                    self.add_failure(platform, locale,
                                     message="Can't verify nonexistent %(platform)s:%(locale)s apk!")
                    continue
                status = self.verify_android_signature(
                    signed_path,
                    script=c['signature_verification_script'],
                    key_alias=c['key_alias'],
                    tools_dir="tools/",
                    env=env,
                )
                if status:
                    self.add_failure(platform, locale,
                                     message="Errors verifying %(platform)s:%(locale)s apk!")
                    # rm to avoid uploading ?
                    self.rmtree(signed_path)

    def upload_signed_bits(self):
        c = self.config
        dirs = self.query_abs_dirs()
        if not c['platforms']:
            self.info("No platforms to rsync! Skipping...")
            return
        rc = self.query_release_config()
        signed_dir = os.path.join(dirs['abs_work_dir'], 'signed')
        ftp_upload_dir = c['ftp_upload_base_dir'] % {
            'version': rc['version'],
            'buildnum': rc['buildnum'],
        }
        if self.rsync_upload_directory(signed_dir, rc['ftp_ssh_key'],
                                       rc['ftp_user'], rc['ftp_server'],
                                       ftp_upload_dir,):
            self.return_code += 1

    def create_snippets(self):
        c = self.config
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        replace_dict = {
            'version': rc['version'],
            'buildnum': rc['buildnum'],
        }
        total_count = {'snippets': 0, 'links': 0}
        success_count = {'snippets': 0, 'links': 0}
        for platform in c['update_platforms']:
            buildid = self.query_buildid(platform, c['buildid_base_url'])
            old_buildid = self.query_buildid(platform, c['old_buildid_base_url'],
                                             buildnum=rc['old_buildnum'],
                                             version=rc['old_version'])
            if not buildid:
                self.add_summary("Can't get buildid for %s! Skipping..." % platform, level=ERROR)
                continue
            replace_dict['platform'] = platform
            replace_dict['buildid'] = buildid
            for locale in locales:
                if self.query_failure(platform, locale):
                    self.warning("%s:%s had previous issues; skipping!" % (platform, locale))
                    continue
                replace_dict['locale'] = locale
                parent_dir = '%s/%s/%s' % (dirs['abs_work_dir'],
                                           platform, locale)
                replace_dict['apk_name'] = c['apk_base_name'] % replace_dict
                signed_path = '%s/%s' % (parent_dir, replace_dict['apk_name'])
                if not os.path.exists(signed_path):
                    self.add_summary("Unable to create snippet for %s:%s: apk doesn't exist!" % (platform, locale), level=ERROR)
                    continue
                size = self.query_filesize(signed_path)
                sha512_hash = self.query_sha512sum(signed_path)
                for channel, channel_dict in c['update_channels'].items():
                    total_count['snippets'] += 1
                    total_count['links'] += 1
                    url = channel_dict['url'] % replace_dict
                    # Create complete snippet
                    self.info("Creating snippet for %s %s %s" % (platform, locale, channel))
                    snippet_dir = "%s/update/%s/Fennec/snippets/%s/%s" % (
                      dirs['abs_work_dir'],
                      channel_dict['dir_base_name'] % (replace_dict),
                      platform, locale)
                    snippet_file = "latest-%s" % channel
                    if self.create_complete_snippet(
                        signed_path, rc['version'], buildid,
                        url, snippet_dir, snippet_file,
                        size, sha512_hash
                    ):
                        success_count['snippets'] += 1
                    else:
                        self.add_failure(platform, locale,
                                         message="Errors creating snippet for %(platform)s:%(locale)s!")
                        continue
                    # Create previous link
                    previous_dir = os.path.join(dirs['abs_work_dir'], 'update',
                                                channel_dict['dir_base_name'] % (replace_dict),
                                                'Fennec', rc['old_version'],
                                                c['update_platform_map'][platform],
                                                old_buildid, locale, channel)
                    self.mkdir_p(previous_dir)
                    self.run_command(["touch", "partial.txt"],
                                     cwd=previous_dir, error_list=BaseErrorList)
                    status = self.run_command(
                        ['ln', '-s',
                         '../../../../../snippets/%s/%s/latest-%s' % (platform, locale, channel),
                         'complete.txt'],
                        cwd=previous_dir, error_list=BaseErrorList
                    )
                    if not status:
                        success_count['links'] += 1
        for k in success_count.keys():
            self.summarize_success_count(success_count[k], total_count[k],
                                         "Created %d of %d " + k + " successfully.")

    def upload_snippets(self):
        c = self.config
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        update_dir = os.path.join(dirs['abs_work_dir'], 'update')
        if not os.path.exists(update_dir):
            self.error("No such directory %s! Skipping..." % update_dir)
            return
        aus_upload_dir = c['aus_upload_base_dir'] % {
            'version': rc['version'],
            'buildnum': rc['buildnum'],
        }
        if self.rsync_upload_directory(update_dir, rc['aus_ssh_key'],
                                       rc['aus_user'], rc['aus_server'],
                                       aus_upload_dir):
            self.return_code += 1



# main {{{1
if __name__ == '__main__':
    sign_android = SignAndroid()
    sign_android.run()
