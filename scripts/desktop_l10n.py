#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""desktop_l10n.py
Desktop repacks
"""

from copy import deepcopy
import os
import re
import subprocess
import sys

try:
    import simplejson as json
    assert json
except ImportError:
    import json

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.log import OutputParser
from mozharness.base.transfer import TransferMixin
from mozharness.base.mar import MarTool, MarFile, MarScripts
from mozharness.base.errors import BaseErrorList, MakefileErrorList
from mozharness.mozilla.release import ReleaseMixin
from mozharness.mozilla.signing import MobileSigningMixin
from mozharness.mozilla.signing import SigningMixin
from mozharness.base.vcs.vcsbase import VCSMixin
from mozharness.mozilla.l10n.locales import LocalesMixin
from mozharness.mozilla.buildbot import BuildbotMixin
from mozharness.mozilla.purge import PurgeMixin
from mozharness.mozilla.mock import MockMixin
from mozharness.base.script import BaseScript

# when running get_output_form_command, pymake has some extra output
# that needs to be filtered out
PyMakeIgnoreList = [
    re.compile(r'''.*make\.py(?:\[\d+\])?: Entering directory'''),
    re.compile(r'''.*make\.py(?:\[\d+\])?: Leaving directory'''),
]


# DesktopSingleLocale {{{1
class DesktopSingleLocale(LocalesMixin, ReleaseMixin, MobileSigningMixin,
                          MockMixin, PurgeMixin, BuildbotMixin, TransferMixin,
                          VCSMixin, SigningMixin, BaseScript):
    """Manages desktop repacks"""
    config_options = [[
        ['--locale', ],
        {"action": "extend",
         "dest": "locales",
         "type": "string",
         "help": "Specify the locale(s) to sign and update"}
    ], [
        ['--locales-file', ],
        {"action": "store",
         "dest": "locales_file",
         "type": "string",
         "help": "Specify a file to determine which locales to sign and update"}
    ], [
        ['--tag-override', ],
        {"action": "store",
         "dest": "tag_override",
         "type": "string",
         "help": "Override the tags set for all repos"}
    ], [
        ['--user-repo-override', ],
        {"action": "store",
         "dest": "user_repo_override",
         "type": "string",
         "help": "Override the user repo path for all repos"}
    ], [
        ['--release-config-file', ],
        {"action": "store",
         "dest": "release_config_file",
         "type": "string",
         "help": "Specify the release config file to use"}
    ], [
        ['--keystore', ],
        {"action": "store",
         "dest": "keystore",
         "type": "string",
         "help": "Specify the location of the signing keystore"}
    ], [
        ['--this-chunk', ],
        {"action": "store",
         "dest": "this_locale_chunk",
         "type": "int",
         "help": "Specify which chunk of locales to run"}
    ], [
        ['--total-chunks', ],
        {"action": "store",
         "dest": "total_locale_chunks",
         "type": "int",
         "help": "Specify the total number of chunks of locales"}
    ], [
        ['--partials-from', ],
        {"action": "store",
         "dest": "partials_from",
         "type": "string",
         "help": "Specify the total number of chunks of locales"}
    ]]

    def __init__(self, require_config_file=True):
        LocalesMixin.__init__(self)
        BaseScript.__init__(
            self,
            config_options=self.config_options,
            all_actions=[
                "clobber",
                "pull",
                "list-locales",
                "setup",
                "repack",
                #"generate-complete-mar",
                #"generate-partials",
                "create-nightly-snippets",
                "upload-nightly-repacks",
                "upload-snippets",
                "summary",
            ],
            require_config_file=require_config_file
        )
        self.buildid = None
        self.make_ident_output = None
        self.repack_env = None
        self.revision = None
        self.version = None
        self.upload_urls = {}
        self.locales_property = {}
        self.l10n_dir = None

        if 'mock_target' in self.config:
            self.enable_mock()

    # Helper methods {{{2
    def query_repack_env(self):
        """returns the env for repacks"""
        if self.repack_env:
            return self.repack_env
        c = self.config
        replace_dict = self.query_abs_dirs()
        if c.get('release_config_file'):
            rc = self.query_release_config()
            replace_dict['version'] = rc['version']
            replace_dict['buildnum'] = rc['buildnum']
        repack_env = self.query_env(partial_env=c.get("repack_env"),
                                    replace_dict=replace_dict)
        if c.get('base_en_us_binary_url') and c.get('release_config_file'):
            rc = self.query_release_config()
            binary_url = c['base_en_us_binary_url'] % replace_dict
            repack_env['EN_US_BINARY_URL'] = binary_url
        if 'MOZ_SIGNING_SERVERS' in os.environ:
            sign_cmd = self.query_moz_sign_cmd(formats=None)
            sign_cmd = subprocess.list2cmdline(sign_cmd)
            # windows fix
            repack_env['MOZ_SIGN_CMD'] = sign_cmd.replace('\\', '\\\\\\\\')
        self.repack_env = repack_env
        return self.repack_env

    def _query_make_ident_output(self):
        """Get |make ident| output from the objdir.
        Only valid after setup is run.
       """
        if self.make_ident_output:
            return self.make_ident_output
        dirs = self.query_abs_dirs()
        self.make_ident_output = self._get_output_from_make(
            target=["ident"],
            cwd=dirs['abs_locales_dir'],
            env=self.query_repack_env())
        return self.make_ident_output

    def query_buildid(self):
        """Get buildid from the objdir.
        Only valid after setup is run.
       """
        if self.buildid:
            return self.buildid
        r = re.compile(r"buildid (\d+)")
        output = self._query_make_ident_output()
        for line in output.splitlines():
            match = r.match(line)
            if match:
                self.buildid = match.groups()[0]
        return self.buildid

    def query_revision(self):
        """Get revision from the objdir.
        Only valid after setup is run.
       """
        if self.revision:
            return self.revision
        r = re.compile(r"^(gecko|fx)_revision ([0-9a-f]{12}\+?)$")
        output = self._query_make_ident_output()
        for line in output.splitlines():
            match = r.match(line)
            if match:
                self.revision = match.groups()[1]
        return self.revision

    def _query_make_variable(self, variable, make_args=None,
                             exclude_lines=PyMakeIgnoreList):
        """returns the value of make echo-variable-<variable>
           it accepts extra make arguements (make_args)
           it also has an exclude_lines from the output filer
           exclude_lines defaults to PyMakeIgnoreList because
           on windows, pymake writes extra output lines that need
           to be filtered out.
        """
        dirs = self.query_abs_dirs()
        make_args = make_args or []
        exclude_lines = exclude_lines or []
        target = ["echo-variable-%s" % variable] + make_args
        cwd = dirs['abs_locales_dir']
        raw_output = self._get_output_from_make(target, cwd=cwd,
                                                env=self.query_repack_env())
        # we want to log all the messages from make/pymake and
        # exlcude some messages from the output ("Entering directory...")
        output = []
        for line in raw_output.split("\n"):
            discard = False
            for element in exclude_lines:
                if element.match(line):
                    discard = True
                    continue
            if not discard:
                output.append(line.strip())
        return " ".join(output).strip()

    def query_base_package_name(self, locale, prettynames=True):
        """Gets the package name from the objdir.
        Only valid after setup is run.
        """
        # optimization:
        # replace locale with %(locale)s
        # and store its values.
        args = ['AB_CD=%s' % locale]
        return self._query_make_variable("PACKAGE", make_args=args)

    def query_version(self):
        """Gets the version from the objdir.
        Only valid after setup is run."""
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
        """returns the upload url for a given locale"""
        if locale in self.upload_urls:
            return self.upload_urls[locale]
        if 'snippet_base_url' in self.config:
            return self.config['snippet_base_url'] % {'locale': locale}
        self.error("Can't determine the upload url for %s!" % locale)
        msg = "You either need to run --upload-repacks before "
        msg += "--create-nightly-snippets, or specify "
        msg += "the 'snippet_base_url' in self.config!"
        self.error(msg)

    def add_failure(self, locale, message, **kwargs):
        self.locales_property[locale] = "Failed"
        prop_key = "%s_failure" % locale
        prop_value = self.query_buildbot_property(prop_key)
        if prop_value:
            prop_value = "%s  %s" % (prop_value, message)
        else:
            prop_value = message
        self.set_buildbot_property(prop_key, prop_value, write_to_file=True)
        BaseScript.add_failure(self, locale, message=message, **kwargs)

    def summary(self):
        """generates a summmary"""
        BaseScript.summary(self)
        # TODO we probably want to make this configurable on/off
        locales = self.query_locales()
        for locale in locales:
            self.locales_property.setdefault(locale, "Success")
        self.set_buildbot_property("locales",
                                   json.dumps(self.locales_property),
                                   write_to_file=True)

    # Actions {{{2
    def clobber(self):
        """clobber"""
        self.read_buildbot_config()
        dirs = self.query_abs_dirs()
        c = self.config
        objdir = os.path.join(dirs['abs_work_dir'], c['mozilla_dir'],
                              c['objdir'])
        PurgeMixin.clobber(self, always_clobber_dirs=[objdir])

    def pull(self):
        """pulls source code"""
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

    def _setup_configure(self, buildid=None):
        """configuration setup"""
        self.enable_mock()
        if self.make_configure():
            self.fatal("Configure failed!")
        self.make_dirs()
        self.make_export(buildid)

    def setup(self):
        """setup step"""
        self.enable_mock()
        dirs = self.query_abs_dirs()
        self._copy_mozconfig()
        self._setup_configure()
        self.make_wget_en_US()
        self.make_unpack()
        revision = self.query_revision()
        if not revision:
            self.fatal("Can't determine revision!")
        # TODO do this through VCSMixin instead of hardcoding hg
        #self.update(dest=dirs["abs_mozilla_dir"], revision=revision)
        hg = self.query_exe("hg")
        self.run_command([hg, "update", "-r", revision],
                         cwd=dirs["abs_mozilla_dir"],
                         env=self.query_repack_env(),
                         error_list=BaseErrorList,
                         halt_on_failure=True)
        self._mar_tools_download()
        # if checkout updates CLOBBER file with a newer timestamp,
        # next make -f client.mk configure  will delete archives
        # downloaded with make wget_en_US, so just touch CLOBBER file
        _clobber_file = self._clobber_file()
        if os.path.exists(_clobber_file):
            self._touch_file(_clobber_file)
        # Configure again since the hg update may have invalidated it.
        buildid = self.query_buildid()
        self._setup_configure(buildid=buildid)

    def _clobber_file(self):
        """returns the full path of the clobber file"""
        c = self.config
        dirs = self.query_abs_dirs()
        return os.path.join(dirs['abs_objdir'], c.get('clobber_file'))

    def _copy_mozconfig(self):
        """copies the mozconfig file into abs_mozilla_dir/.mozconfig
           and logs the content
        """
        c = self.config
        dirs = self.query_abs_dirs()
        src = os.path.join(dirs['abs_work_dir'], c['mozconfig'])
        dst = os.path.join(dirs['abs_mozilla_dir'], '.mozconfig')
        self.copyfile(src, dst)

        # STUPID HACK HERE
        # should we update the mozconfig so it has the right value?
        with open(src, 'r') as in_mozconfig:
            with open(dst, 'w') as out_mozconfig:
                for line in in_mozconfig:
                    if 'with-l10n-base' in line:
                        line = 'ac_add_options --with-l10n-base=../../l10n\n'
                        self.l10n_dir = line.partition('=')[2].strip()
                    out_mozconfig.write(line)
        # now log
        with open(dst, 'r') as mozconfig:
            for line in mozconfig:
                self.info(line.strip())

    def _make(self, target, cwd, env, error_list=MakefileErrorList,
              halt_on_failure=True):
        """runs make and retrurns the exit code"""
        self.enable_mock()
        make = self.query_exe("make", return_type="list")
        return self.run_command(make + target,
                                cwd=cwd,
                                env=env,
                                error_list=error_list,
                                halt_on_failure=halt_on_failure)

    def _get_output_from_make(self, target, cwd, env, halt_on_failure=True):
        """runs make and returns the output of the command"""
        self.enable_mock()
        make = self.query_exe("make", return_type="list")
        return self.get_output_from_command(make + target,
                                            cwd=cwd,
                                            env=env,
                                            silent=True,
                                            halt_on_failure=halt_on_failure)

    def make_configure(self):
        """calls make -f client.mk configure"""
        env = self.query_repack_env()
        dirs = self.query_abs_dirs()
        cwd = dirs['abs_mozilla_dir']
        target = ["-f", "client.mk", "configure"]
        return self._make(target=target, cwd=cwd, env=env)

    def make_dirs(self):
        """calls make <dirs>
           dirs is defined in configuration"""
        c = self.config
        env = self.query_repack_env()
        dirs = self.query_abs_dirs()
        target = []
        for make_dir in c.get('make_dirs', []):
            cwd = os.path.join(dirs['abs_objdir'], make_dir)
            self._make(target=target, cwd=cwd, env=env, halt_on_failure=True)

    def make_export(self, buildid):
        """calls make export <buildid>"""
        #is it really needed ???
        if buildid is None:
            return
        dirs = self.query_abs_dirs()
        cwd = dirs['abs_locales_dir']
        env = self.query_repack_env()
        target = ["export", 'MOZ_BUILD_DATE=%s' % str(buildid)]
        return self._make(target=target, cwd=cwd, env=env)

    def make_unpack(self):
        """wrapper for make unpack"""
        c = self.config
        dirs = self.query_abs_dirs()
        env = self.query_repack_env()
        cwd = os.path.join(dirs['abs_objdir'], c['locales_dir'])
        return self._make(target=["unpack"], cwd=cwd, env=env)

    def make_wget_en_US(self):
        """wrapper for make wget-en-US"""
        env = self.query_repack_env()
        dirs = self.query_abs_dirs()
        cwd = dirs['abs_locales_dir']
        return self._make(target=["wget-en-US"], cwd=cwd, env=env)

    def make_installers(self, locale):
        """wrapper for make installers-(locale)"""
        env = self.query_repack_env()
        env['L10NBASEDIR'] = self.l10n_dir
        self._mar_tools_download()
        # make.py: error: l10n-base required when using locale-mergedir
        # adding a replace(...) because make.py doesn't like
        # --locale-mergedir=e:\...\...\...
        # replacing \ with /
        # this kind of hacks makes me sad
        env['LOCALE_MERGEDIR'] = env['LOCALE_MERGEDIR'].replace("\\", "/")
        dirs = self.query_abs_dirs()
        cwd = os.path.join(dirs['abs_locales_dir'])
        target = ["installers-%s" % locale,
                  "LOCALE_MERGEDIR=%s" % env["LOCALE_MERGEDIR"]]
        return self._make(target=target, cwd=cwd,
                          env=env, halt_on_failure=False)

    def generate_complete_mar(self, locale):
        """creates a complete mar file"""
        c = self.config
        dirs = self.query_abs_dirs()
        self.create_mar_dirs()
        self._mar_tools_download()
        package_basedir = os.path.join(dirs['abs_objdir'],
                                       c['package_base_dir'])
        env = self.query_repack_env()
        cmd = os.path.join(dirs['abs_objdir'], c['update_packaging_dir'])
        cmd = ['-C', cmd, 'full-update', 'AB_CD=%s' % locale,
               'PACKAGE_BASE_DIR=%s' % package_basedir]
        self._make(target=cmd, cwd=dirs['abs_mozilla_dir'], env=env)

    def repack(self):
        """creates the repacks and udpates"""
        # TODO per-locale logs and reporting.
        self.enable_mock()
        locales = self.query_locales()
        results = {}
        for locale in locales:
            compare_locales = self.run_compare_locales(locale)
            installers = self.make_installers(locale)
            partials = self.generate_partials(locale)
            # log results:
            result = {}
            result['compare_locales'] = compare_locales
            result['installers'] = installers
            result['partials'] = partials
            results[locale] = result
        for locale in results:
            self.info(locale)
            steps = results[locale]
            for step in steps:
                self.info("%s: %s" % (step, steps[step]))

    def upload_repacks(self):
        """calls make upload <locale>"""
        c = self.config
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        version = self.query_version()
        upload_env = self.query_repack_env()
        success_count = total_count = 0
        cwd = dirs['abs_locales_dir']
        for locale in locales:
            if self.query_failure(locale):
                self.warning("Skipping previously failed locale %s." % locale)
                continue
            total_count += 1
            if c.get('base_post_upload_cmd'):
                upload_cmd = c['base_post_upload_cmd'] % {'version': version,
                                                          'locale': locale}
                upload_env['POST_UPLOAD_CMD'] = upload_cmd
            target = ["upload", "AB_CD=%s" % locale]
            output = self._get_output_from_make(target, cwd=cwd, env=upload_env)
            parser = OutputParser(config=self.config, log_obj=self.log_obj,
                                  error_list=MakefileErrorList)
            parser.add_lines(output)
            if parser.num_errors:
                msg = "%s failed in make upload!" % (locale)
                self.add_failure(locale, message=msg)
                continue
            package_name = self.query_base_package_name(locale)
            r = re.compile("(http.*%s)" % package_name)
            success = False
            for line in output.splitlines():
                m = r.match(line)
                if m:
                    self.upload_urls[locale] = m.groups()[0]
                    self.info("Found upload url %s" % self.upload_urls[locale])
                    success = True
            if not success:
                msg = "Failed to detect %s url in make upload!" % locale
                self.add_failure(locale, message=msg)
                self.debug(output)
                continue
            success_count += 1
            msg = "Uploaded %d of %d binaries successfully."
        self.summarize_success_count(success_count, total_count, message=msg)

    def create_nightly_snippets(self):
        """create snippets for nightly"""
        c = self.config
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        buildid = self.query_buildid()
        version = self.query_version()
        success_count = total_count = 0
        for locale in locales:
            total_count += 1
            aus_dir = c['aus_base_dir'] % {'buildid': buildid,
                                           'build_target': c['build_target'],
                                           'locale': locale}
            aus_abs_dir = os.path.join(dirs['abs_work_dir'], 'update', aus_dir)
            base_name = self.query_base_package_name(locale)
            binary_path = os.path.join(self._abs_dist_dir(), base_name)
            # for win repacks
            binary_path = binary_path.replace(os.sep, "/")
            url = self.query_upload_url(locale)
            if not url:
                msg = "Can't create a snippet for %s " % locale
                msg += "without an upload url."
                self.add_failure(locale, msg)
                continue
            if not self.create_complete_snippet(binary_path, version,
                                                buildid, url, aus_abs_dir):
                msg = "Errors creating snippet for %s! " % locale
                msg += "Removing snippet directory."
                self.add_failure(locale, message=msg)
                self.rmtree(aus_abs_dir)
                continue
            self._touch_file(os.path.join(aus_abs_dir, "partial.txt"))
            success_count += 1
            msg = "Created %d of %d snippets successfully."
        self.summarize_success_count(success_count, total_count, message=msg)

    def upload_nightly_snippets(self):
        """uploads nightly snippets"""
        c = self.config
        dirs = self.query_abs_dirs()
        update_dir = os.path.join(dirs['abs_work_dir'], 'update')
        if not os.path.exists(update_dir):
            self.error("No such directory %s! Skipping..." % update_dir)
            return
        if self.rsync_upload_directory(update_dir, c['aus_ssh_key'],
                                       c['aus_user'], c['aus_server'],
                                       c['aus_upload_basedir']):
            self.return_code += 1

    def generate_partials(self, locale):
        """generate partial files"""
        c = self.config
        version = self.query_version()
        update_mar_dir = self.update_mar_dir()
        incremental_update = self._incremental_update_script()
        env = self.query_repack_env()
        mar_scripts = MarScripts(unpack=self._unpack_script(),
                                 incremental_update=incremental_update,
                                 tools_dir=self._mar_tool_dir(),
                                 ini_file=c['application_ini'],
                                 mar_binaries=self._mar_binaries(),
                                 env=env)
        localized_mar = c['localized_mar'] % {'version': version,
                                              'locale': locale}
        localized_mar = os.path.join(self._mar_dir('update_mar_dir'),
                                     localized_mar)

        if not os.path.exists(localized_mar):
            # *.complete.mar already exist in windows but
            # it does not exist on other platforms
            self.info("%s does not exist. Creating it." % localized_mar)
            self.generate_complete_mar(locale)

        to_m = MarFile(mar_scripts,
                       log_obj=self.log_obj,
                       filename=localized_mar,
                       prettynames='1')
        from_m = MarFile(mar_scripts,
                         log_obj=self.log_obj,
                         filename=self.get_previous_mar(locale),
                         prettynames='1')
        archive = c['partial_mar'] % {'version': version,
                                      'locale': locale,
                                      'from_buildid': from_m.buildid(),
                                      'to_buildid': to_m.buildid()}
        archive = os.path.join(update_mar_dir, archive)
        # let's make the incremental update
        to_m.incremental_update(from_m, archive)

    def delete_pgc_files(self):
        """deletes pgc files"""
        for directory in (self.previous_mar_dir(),
                          self.current_mar_dir()):
            for pcg_file in self.pgc_files(directory):
                self.info("removing %s" % pcg_file)
                self.rmtree(pcg_file)

    def _previous_mar_url(self, locale):
        """returns the url for previous mar"""
        c = self.config
        base_url = c['previous_mar_url']
        return "/".join((base_url, self._localized_mar(locale)))

    def get_previous_mar(self, locale):
        """downloads the previous mar file"""
        self.mkdir_p(self.previous_mar_dir())
        self.download_file(self._previous_mar_url(locale),
                           self._previous_mar_filename())
        return self._previous_mar_filename()

    def _localized_mar(self, locale):
        c = self.config
        version = self.query_version()
        return c["localized_mar"] % {'version': version, 'locale': locale}

    def _previous_mar_filename(self):
        """returns the complete path to previous.mar"""
        c = self.config
        return os.path.join(self.previous_mar_dir(), c['previous_mar_filename'])

    def create_mar_dirs(self):
        """creates mar directories: previous/ current/"""
        for d in (self.previous_mar_dir(),
                  self.current_mar_dir()):
            self.info("creating: %s" % d)
            self.mkdir_p(d)

    def delete_mar_dirs(self):
        """delete mar directories: previous, current"""
        for directory in (self.previous_mar_dir(),
                          self.current_mar_dir(),
                          self.current_work_mar_dir()):
            self.info("deleting: %s" % directory)
            if os.path.exists(directory):
                self.rmtree(directory)

    def _mar_tool_dir(self):
        """full path to the tools/ directory"""
        c = self.config
        dirs = self.query_abs_dirs()
        return os.path.join(dirs['abs_objdir'], c["local_mar_tool_dir"])

    def _mar_tools_download(self):
        """downloads mar and mbsdiff files"""
        c = self.config
        martool = MarTool(c['mar_tools_url'], self._mar_tool_dir(),
                          self.log_obj, self._mar_binaries())
        martool.download()

    def _incremental_update_script(self):
        """incremental update script"""
        c = self.config
        dirs = self.query_abs_dirs()
        return os.path.join(dirs['abs_mozilla_dir'], c['incremental_update_script'])

    def _unpack_script(self):
        """unpack script full path"""
        c = self.config
        dirs = self.query_abs_dirs()
        return os.path.join(dirs['abs_mozilla_dir'], c['unpack_script'])

    def previous_mar_dir(self):
        """returns the full path of the previous/ directory"""
        return self._mar_dir('previous_mar_dir')

    def _abs_dist_dir(self):
        """returns the full path to abs_objdir/dst"""
        dirs = self.query_abs_dirs()
        return os.path.join(dirs['abs_objdir'], 'dist')

    def update_mar_dir(self):
        """returns the full path of the update/ directory"""
        return self._mar_dir('update_mar_dir')

    def current_mar_dir(self):
        """returns the full path of the current/ directory"""
        return self._mar_dir('current_mar_dir')

    def current_work_mar_dir(self):
        """returns the full path to current.work"""
        return self._mar_dir('current_work_mar_dir')

    def _mar_binaries(self):
        c = self.config
        return (c['mar'], c['mbsdiff'])

    def _mar_dir(self, dirname):
        """returns the full path of dirname;
            dirname is an entry in configuration"""
        c = self.config
        return os.path.join(self.get_objdir(), c.get(dirname))

    def get_objdir(self):
        """returns full path to objdir"""
        dirs = self.query_abs_dirs()
        return dirs['abs_objdir']

    def pgc_files(self, basedir):
        """returns a list of .pcf files in basedir"""
        pgc_files = []
        for dirpath, files, dirs in os.walk(basedir):
            for f in files:
                if f.endswith('.pgc'):
                    pgc_files.append(os.path.join(dirpath, f))
        return pgc_files


# main {{{
if __name__ == '__main__':
    single_locale = DesktopSingleLocale()
    single_locale.run_and_exit()
