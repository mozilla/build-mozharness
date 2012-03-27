#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""mobile_l10n.py

This currently supports nightly and release single locale repacks for
Android.  This also creates nightly updates.
"""

from copy import deepcopy
import os
import re
import sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import BaseErrorList, MakefileErrorList
from mozharness.base.log import OutputParser
from mozharness.base.transfer import TransferMixin
from mozharness.mozilla.release import ReleaseMixin
from mozharness.mozilla.signing import MobileSigningMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.l10n.locales import LocalesMixin



# MobileSingleLocale {{{1
class MobileSingleLocale(LocalesMixin, ReleaseMixin, MobileSigningMixin,
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
      "help": "Specify a file to determine which locales to sign and update"
     }
    ],[
     ['--tag-override',],
     {"action": "store",
      "dest": "tag_override",
      "type": "string",
      "help": "Override the tags set for all repos"
     }
    ],[
     ['--user-repo-override',],
     {"action": "store",
      "dest": "user_repo_override",
      "type": "string",
      "help": "Override the user repo path for all repos"
     }
    ],[
     ['--release-config-file',],
     {"action": "store",
      "dest": "release_config_file",
      "type": "string",
      "help": "Specify the release config file to use"
     }
    ],[
     ['--keystore',],
     {"action": "store",
      "dest": "keystore",
      "type": "string",
      "help": "Specify the location of the signing keystore"
     }
    ],[
     ['--this-chunk',],
     {"action": "store",
      "dest": "this_locale_chunk",
      "type": "int",
      "help": "Specify which chunk of locales to run"
     }
    ],[
     ['--total-chunks',],
     {"action": "store",
      "dest": "total_locale_chunks",
      "type": "int",
      "help": "Specify the total number of chunks of locales"
     }
    ]]

    def __init__(self, require_config_file=True):
        LocalesMixin.__init__(self)
        MercurialScript.__init__(self,
            config_options=self.config_options,
            all_actions=[
                "clobber",
                "pull",
                "list-locales",
                "setup",
                "repack",
                "upload-repacks",
                "create-nightly-snippets",
                "upload-nightly-snippets",
            ],
            require_config_file=require_config_file
        )
        self.base_package_name = None
        self.buildid = None
        self.make_ident_output = None
        self.repack_env = None
        self.revision = None
        self.upload_env = None
        self.version = None
        self.upload_urls = {}

    # Helper methods {{{2
    def query_repack_env(self):
        if self.repack_env:
            return self.repack_env
        c = self.config
        replace_dict = {}
        if c.get('release_config_file'):
            rc = self.query_release_config()
            replace_dict = {
                'version': rc['version'],
                'buildnum': rc['buildnum']
            }
        repack_env = self.query_env(partial_env=c.get("repack_env"),
                                    replace_dict=replace_dict)
        if c.get('base_en_us_binary_url') and c.get('release_config_file'):
            rc = self.query_release_config()
            repack_env['EN_US_BINARY_URL'] = c['base_en_us_binary_url'] % replace_dict
        self.repack_env = repack_env
        return self.repack_env

    def query_upload_env(self):
        if self.upload_env:
            return self.upload_env
        c = self.config
        buildid = self.query_buildid()
        version = self.query_version()
        upload_env = self.query_env(partial_env=c.get("upload_env"),
                                    replace_dict={'buildid': buildid,
                                                  'version': version})
        self.upload_env = upload_env
        return self.upload_env

    def _query_make_ident_output(self):
        """Get |make ident| output from the objdir.
        Only valid after setup is run.
        """
        if self.make_ident_output:
            return self.make_ident_output
        env = self.query_repack_env()
        dirs = self.query_abs_dirs()
        output = self.get_output_from_command(["make", "ident"],
                                              cwd=dirs['abs_locales_dir'],
                                              env=env,
                                              silent=True,
                                              halt_on_failure=True)
        parser = OutputParser(config=self.config, log_obj=self.log_obj,
                              error_list=MakefileErrorList)
        parser.add_lines(output)
        self.make_ident_output = output
        return output

    def query_buildid(self):
        """Get buildid from the objdir.
        Only valid after setup is run.
        """
        if self.buildid:
            return self.buildid
        r = re.compile("buildid (\d+)")
        output = self._query_make_ident_output()
        for line in output.splitlines():
            m = r.match(line)
            if m:
                self.buildid = m.groups()[0]
        return self.buildid

    def query_revision(self):
        """Get revision from the objdir.
        Only valid after setup is run.
        """
        if self.revision:
            return self.revision
        r = re.compile(r"gecko_revision ([0-9a-f]{12}\+?)")
        output = self._query_make_ident_output()
        for line in output.splitlines():
            m = r.match(line)
            if m:
                self.revision = m.groups()[0]
        return self.revision

    def _query_make_variable(self, variable, make_args=None):
        make = self.query_exe('make')
        env = self.query_repack_env()
        dirs = self.query_abs_dirs()
        if make_args is None:
            make_args = []
        # TODO error checking
        output = self.get_output_from_command(
            [make, "echo-variable-%s" % variable] + make_args,
            cwd=dirs['abs_locales_dir'], silent=True,
            env=env
        )
        parser = OutputParser(config=self.config, log_obj=self.log_obj,
                              error_list=MakefileErrorList)
        parser.add_lines(output)
        return output.strip()

    def query_base_package_name(self):
        """Get the package name from the objdir.
        Only valid after setup is run.
        """
        if self.base_package_name:
            return self.base_package_name
        self.base_package_name = self._query_make_variable(
            "PACKAGE",
            make_args=['AB_CD=%(locale)s']
        )
        return self.base_package_name

    def query_version(self):
        """Get the package name from the objdir.
        Only valid after setup is run.
        """
        if self.version:
            return self.version
        c = self.config
        if c.get('release_config_file'):
            rc = self.query_release_config()
            self.version = rc['version']
        else:
            self.version = self._query_make_variable("MOZ_APP_VERSION")
        return self.version

    def query_upload_url(self, locale):
        if locale in self.upload_urls:
            return self.upload_urls[locale]
        if 'snippet_base_url' in self.config:
            return self.config['snippet_base_url'] % {'locale': locale}
        self.error("Can't determine the upload url for %s!" % locale)
        self.error("You either need to run --upload-repacks before --create-nightly-snippets, or specify the 'snippet_base_url' in self.config!")

    # Actions {{{2
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
        self.pull_locale_source()

    # list_locales() is defined in LocalesMixin.

    def preflight_setup(self):
        if 'clobber' not in self.actions:
            c = self.config
            dirs = self.query_abs_dirs()
            objdir = os.path.join(dirs['abs_work_dir'], c['mozilla_dir'],
                                  c['objdir'])
            self.rmtree(objdir)

    def setup(self):
        c = self.config
        dirs = self.query_abs_dirs()
        mozconfig_path = os.path.join(dirs['abs_mozilla_dir'], '.mozconfig')
        self.copyfile(os.path.join(dirs['abs_work_dir'], c['mozconfig']),
                      mozconfig_path)
        # TODO stop using cat
        cat = self.query_exe("cat")
        hg = self.query_exe("hg")
        make = self.query_exe("make")
        self.run_command([cat, mozconfig_path])
        env = self.query_repack_env()
        self.run_command([make, "-f", "client.mk", "configure"],
                         cwd=dirs['abs_mozilla_dir'],
                         env=env,
                         error_list=MakefileErrorList,
                         halt_on_failure=True)
        for make_dir in c.get('make_dirs', []):
            self.run_command([make],
                             cwd=os.path.join(dirs['abs_objdir'], make_dir),
                             env=env,
                             error_list=MakefileErrorList,
                             halt_on_failure=True)
        self.run_command([make, "wget-en-US"],
                         cwd=dirs['abs_locales_dir'],
                         env=env,
                         error_list=MakefileErrorList,
                         halt_on_failure=True)
        self.run_command([make, "unpack"],
                         cwd=dirs['abs_locales_dir'],
                         env=env,
                         error_list=MakefileErrorList,
                         halt_on_failure=True)
        revision = self.query_revision()
        if not revision:
            self.fatal("Can't determine revision!")
        # TODO do this through VCSMixin instead of hardcoding hg
        self.run_command([hg, "update", "-r", revision],
                         cwd=dirs["abs_mozilla_dir"],
                         env=env,
                         error_list=BaseErrorList,
                         halt_on_failure=True)

    def repack(self):
        # TODO per-locale logs and reporting.
        c = self.config
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        make = self.query_exe("make")
        repack_env = self.query_repack_env()
        base_package_name = self.query_base_package_name()
        base_package_dir = os.path.join(dirs['abs_objdir'], 'dist')
        success_count = total_count = 0
        for locale in locales:
            total_count += 1
            if self.run_compare_locales(locale):
                self.add_failure(locale, message="%s failed in compare-locales!" % locale)
                continue
            if self.run_command([make, "installers-%s" % locale],
                                cwd=dirs['abs_locales_dir'],
                                env=repack_env,
                                error_list=MakefileErrorList,
                                halt_on_failure=False):
                self.add_failure(locale, message="%s failed in make installers-%s!" % (locale, locale))
                continue
            signed_path = os.path.join(base_package_dir,
                                       base_package_name % {'locale': locale})
            status = self.verify_android_signature(
                signed_path,
                script=c['signature_verification_script'],
                env=repack_env
            )
            if status:
                self.add_failure(locale, message="Errors verifying %s binary!" % locale)
                # No need to rm because upload is per-locale
                continue
            success_count += 1
        self.summarize_success_count(success_count, total_count,
                                     message="Repacked %d of %d binaries successfully.")

    def upload_repacks(self):
        c = self.config
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        make = self.query_exe("make")
        base_package_name = self.query_base_package_name()
        version = self.query_version()
        upload_env = self.query_upload_env()
        success_count = total_count = 0
        for locale in locales:
            if self.query_failure(locale):
                self.warning("Skipping previously failed locale %s." % locale)
                continue
            total_count += 1
            if c.get('base_post_upload_cmd'):
                upload_env['POST_UPLOAD_CMD'] = c['base_post_upload_cmd'] % {'version': version, 'locale': locale}
            output = self.get_output_from_command(
                # Ugly hack to avoid |make upload| stderr from showing up
                # as get_output_from_command errors
                "%s upload AB_CD=%s 2>&1" % (make, locale),
                cwd=dirs['abs_locales_dir'],
                env=upload_env,
                silent=True
            )
            parser = OutputParser(config=self.config, log_obj=self.log_obj,
                                  error_list=MakefileErrorList)
            parser.add_lines(output)
            if parser.num_errors:
                self.add_failure(locale, message="%s failed in make upload!" % (locale))
                continue
            package_name = base_package_name % {'locale': locale}
            r = re.compile("(http.*%s)" % package_name)
            success = False
            for line in output.splitlines():
                m = r.match(line)
                if m:
                    self.upload_urls[locale] = m.groups()[0]
                    self.info("Found upload url %s" % self.upload_urls[locale])
                    success = True
            if not success:
                self.add_failure(locale, message="Failed to detect %s url in make upload!" % (locale))
                print output
                continue
            success_count += 1
        self.summarize_success_count(success_count, total_count,
                                     message="Uploaded %d of %d binaries successfully.")

    def create_nightly_snippets(self):
        c = self.config
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        base_package_name = self.query_base_package_name()
        buildid = self.query_buildid()
        version = self.query_version()
        binary_dir = os.path.join(dirs['abs_objdir'], 'dist')
        success_count = total_count = 0
        replace_dict = {
            'buildid': buildid,
            'build_target': c['build_target'],
        }
        for locale in locales:
            total_count += 1
            replace_dict['locale'] = locale
            aus_base_dir = c['aus_base_dir'] % replace_dict
            aus_abs_dir = os.path.join(dirs['abs_work_dir'], 'update',
                                       aus_base_dir)
            binary_path = os.path.join(binary_dir,
                                       base_package_name % {'locale': locale})
            url = self.query_upload_url(locale)
            if not url:
                self.add_failure(locale, "Can't create a snippet for %s without an upload url." % locale)
                continue
            if not self.create_complete_snippet(binary_path, version, buildid, url, aus_abs_dir):
                self.add_failure(locale, message="Errors creating snippet for %s!  Removing snippet directory." % locale)
                self.rmtree(aus_abs_dir)
                continue
            self.run_command(["touch", os.path.join(aus_abs_dir, "partial.txt")])
            success_count += 1
        self.summarize_success_count(success_count, total_count,
                                     message="Created %d of %d snippets successfully.")

    def upload_nightly_snippets(self):
        c = self.config
        dirs = self.query_abs_dirs()
        update_dir = os.path.join(dirs['abs_work_dir'], 'update')
        if not os.path.exists(update_dir):
            self.error("No such directory %s! Skipping..." % update_dir)
            return
        if self.rsync_upload_directory(update_dir, c['aus_ssh_key'],
                                       c['aus_user'], c['aus_server'],
                                       c['aus_upload_dir']):
            self.return_code += 1



# main {{{1
if __name__ == '__main__':
    single_locale = MobileSingleLocale()
    single_locale.run()
