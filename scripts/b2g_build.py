#!/usr/bin/env python
# Mozilla licence shtuff

import sys
import os
import glob
import re
import tempfile
from datetime import datetime
import urllib2
import urlparse
import time
import xml.dom.minidom

try:
    import simplejson as json
except ImportError:
    import json

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

# import the guts
from mozharness.base.config import parse_config_file
from mozharness.base.script import BaseScript
from mozharness.base.vcs.vcsbase import VCSMixin
from mozharness.base.transfer import TransferMixin
from mozharness.base.errors import MakefileErrorList
from mozharness.base.log import WARNING, ERROR, INFO, FATAL
from mozharness.mozilla.l10n.locales import GaiaLocalesMixin, LocalesMixin
from mozharness.mozilla.mock import MockMixin
from mozharness.mozilla.tooltool import TooltoolMixin
from mozharness.mozilla.buildbot import BuildbotMixin
from mozharness.mozilla.purge import PurgeMixin
from mozharness.mozilla.signing import SigningMixin

# B2G builds complain about java...but it doesn't seem to be a problem
# Let's turn those into WARNINGS instead
B2GMakefileErrorList = MakefileErrorList + [
    {'substr': r'''NS_ERROR_FILE_ALREADY_EXISTS: Component returned failure code''', 'level': ERROR},
]
B2GMakefileErrorList.insert(0, {'substr': r'/bin/bash: java: command not found', 'level': WARNING})


class B2GBuild(LocalesMixin, MockMixin, BaseScript, VCSMixin, TooltoolMixin, TransferMixin,
               BuildbotMixin, PurgeMixin, GaiaLocalesMixin, SigningMixin):
    config_options = [
        [["--repo"], {
            "dest": "repo",
            "help": "which gecko repo to check out",
        }],
        [["--gonk-snapshot"], {
            "dest": "gonk_snapshot_url",
            "help": "override the gonk snapshot specified in the build config",
        }],
        [["--target"], {
            "dest": "target",
            "help": "specify which build type to do",
        }],
        [["--b2g-config-dir"], {
            "dest": "b2g_config_dir",
            "help": "specify which in-tree config directory to use, relative to b2g/config/ (defaults to --target)",
        }],
        [["--gecko-config"], {
            "dest": "gecko_config",
            "help": "specfiy alternate location for gecko config",
        }],
        [["--disable-ccache"], {
            "dest": "ccache",
            "action": "store_false",
            "help": "disable ccache",
        }],
        [["--gaia-languages-file"], {
            "dest": "gaia_languages_file",
            "help": "languages file for gaia multilocale profile",
        }],
        [["--gecko-languages-file"], {
            "dest": "locales_file",
            "help": "languages file for gecko multilocale",
        }],
        [["--gecko-l10n-base-dir"], {
            "dest": "l10n_dir",
            "help": "dir to clone gecko l10n repos into, relative to the work directory",
        }],
        [["--merge-locales"], {
            "dest": "merge_locales",
            "help": "Dummy option to keep from burning. We now always merge",
        }],
        [["--variant"], {
            "dest": "variant",
            "help": "b2g build variant. overrides gecko config's value",
        }],
        [["--checkout-revision"], {
            "dest": "checkout_revision",
            "help": "checkout a specific gecko revision.",
        }],
        [["--additional-source-tarballs"], {
            "action": "extend",
            "type": "string",
            "dest": "additional_source_tarballs",
            "help": "Additional source tarballs to extract",
        }],
    ]

    def __init__(self, require_config_file=False):
        self.gecko_config = None
        self.buildid = None
        LocalesMixin.__init__(self)
        BaseScript.__init__(self,
                            config_options=self.config_options,
                            all_actions=[
                                'clobber',
                                'checkout-gecko',
                                # Download via tooltool repo in gecko checkout or via explicit url
                                'download-gonk',
                                'unpack-gonk',
                                'checkout-gaia',
                                'checkout-gaia-l10n',
                                'checkout-gecko-l10n',
                                'checkout-compare-locales',
                                'update-source-manifest',
                                'build',
                                'build-symbols',
                                'make-updates',
                                'build-update-testdata',
                                'prep-upload',
                                'upload',
                                'make-update-xml',
                                'upload-updates',
                                'make-socorro-json',
                                'upload-source-manifest',
                            ],
                            default_actions=[
                                'checkout-gecko',
                                'download-gonk',
                                'unpack-gonk',
                                'build',
                            ],
                            require_config_file=require_config_file,

                            # Default configuration
                            config={
                                'default_vcs': 'hgtool',
                                'vcs_share_base': os.environ.get('HG_SHARE_BASE_DIR'),
                                'ccache': True,
                                'buildbot_json_path': os.environ.get('PROPERTIES_FILE'),
                                'tooltool_servers': None,
                                'ssh_key': None,
                                'ssh_user': None,
                                'upload_remote_host': None,
                                'upload_remote_basepath': None,
                                'enable_try_uploads': False,
                                'tools_repo': 'http://hg.mozilla.org/build/tools',
                                'locales_dir': 'gecko/b2g/locales',
                                'l10n_dir': 'gecko-l10n',
                                'ignore_locales': ['en-US', 'multi'],
                                'locales_file': 'gecko/b2g/locales/all-locales',
                                'mozilla_dir': 'build/gecko',
                                'objdir': 'build/objdir-gecko',
                                'merge_locales': True,
                                'compare_locales_repo': 'http://hg.mozilla.org/build/compare-locales',
                                'compare_locales_rev': 'RELEASE_AUTOMATION',
                                'compare_locales_vcs': 'hgtool',
                            },
                            )

        dirs = self.query_abs_dirs()
        self.objdir = os.path.join(dirs['work_dir'], 'objdir-gecko')
        self.marfile = "%s/dist/b2g-update/b2g-gecko-update.mar" % self.objdir
        self.application_ini = os.path.join(
            dirs['work_dir'], 'out', 'target', 'product',
            self.config['target'], 'system', 'b2g', 'application.ini')

    def _pre_config_lock(self, rw_config):
        super(B2GBuild, self)._pre_config_lock(rw_config)

        if self.buildbot_config is None:
            self.info("Reading buildbot build properties...")
            self.read_buildbot_config()

        if 'target' not in self.config:
            self.fatal("Must specify --target!")

        if not (self.buildbot_config and 'properties' in self.buildbot_config) and 'repo' not in self.config:
            self.fatal("Must specify --repo")

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = LocalesMixin.query_abs_dirs(self)

        c = self.config
        dirs = {
            'src': os.path.join(c['work_dir'], 'gecko'),
            'work_dir': abs_dirs['abs_work_dir'],
            'testdata_dir': os.path.join(abs_dirs['abs_work_dir'], 'testdata'),
            'gaia_l10n_base_dir': os.path.join(abs_dirs['abs_work_dir'], 'gaia-l10n'),
            'compare_locales_dir': os.path.join(abs_dirs['abs_work_dir'], 'compare-locales'),
        }

        abs_dirs.update(dirs)
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def load_gecko_config(self):
        if self.gecko_config:
            return self.gecko_config

        dirs = self.query_abs_dirs()
        conf_file = self.config.get('gecko_config')
        if conf_file is None:
            conf_file = os.path.join(
                dirs['src'], 'b2g', 'config',
                self.config.get('b2g_config_dir', self.config['target']),
                'config.json'
            )
        self.info("gecko_config file: %s" % conf_file)
        self.run_command(['cat', conf_file])
        self.gecko_config = json.load(open(conf_file))
        return self.gecko_config

    def query_repo(self):
        if self.buildbot_config and 'properties' in self.buildbot_config:
            return 'http://hg.mozilla.org/%s' % self.buildbot_config['properties']['repo_path']
        else:
            return self.config['repo']

    def query_branch(self):
        if self.buildbot_config and 'properties' in self.buildbot_config:
            return self.buildbot_config['properties']['branch']
        else:
            return os.path.basename(self.query_repo())

    def query_buildid(self):
        if self.buildid:
            return self.buildid
        dirs = self.query_abs_dirs()
        platform_ini = os.path.join(dirs['work_dir'], 'out', 'target',
                                    'product', self.config['target'], 'system',
                                    'b2g', 'platform.ini')
        data = self.read_from_file(platform_ini)
        buildid = re.search("^BuildID=(\d+)$", data, re.M)
        if buildid:
            self.buildid = buildid.group(1)
            return self.buildid

    def query_version(self):
        data = self.read_from_file(self.application_ini)
        version = re.search("^Version=(.+)$", data, re.M)
        if version:
            return version.group(1)

    def query_revision(self):
        if 'revision' in self.buildbot_properties:
            return self.buildbot_properties['revision']

        if self.buildbot_config and 'sourcestamp' in self.buildbot_config:
            return self.buildbot_config['sourcestamp']['revision']

        return None

    def query_translated_revision(self, url, project, rev, attempts=30, sleeptime=30,
                                  project_name=None):
        if project_name is None:
            project_name = project
        url = '%s/%s/git/%s' % (url, project, rev)
        self.info('Mapping %s revision from hg to git using %s' % (project_name, url))
        n = 1
        while n <= attempts:
            try:
                r = urllib2.urlopen(url, timeout=10)
                j = json.loads(r.readline())
                if j['git_rev'] is None:
                    # allow for user repos in staging
                    if self.config.get("require_git_rev", True):
                        raise Exception("Mapper returned a git revision of None; maybe it needs more time.")
                    else:
                        self.warning("Mapper returned a git revision of None.  Accepting because require_git_rev is False.")
                return j['git_rev']
            except Exception, err:
                self.warning('Error: %s' % str(err))
                if n == attempts:
                    self.fatal('Giving up on %s git revision for %s.' % (project_name, rev))
                if sleeptime > 0:
                    self.info('Sleeping %i seconds before retrying' % sleeptime)
                    time.sleep(sleeptime)
                continue
            finally:
                n += 1

    def get_hg_commit_time(self, repo_dir, rev):
        """Returns the commit time for given `rev` in unix epoch time"""
        hg = self.query_exe('hg')
        cmd = [
            hg,
            'log',
            '-R', repo_dir,
            '-r', rev,
            '--template', '{date|hgdate}'
        ]
        try:
            # {date|hgdate} returns a space-separated tuple of unixtime,
            # timezone offset
            output = self.get_output_from_command(cmd)
        except Exception:
            # Failed to run hg for some reason
            self.exception("failed to run hg log; using timestamp of 0 instead", level=WARNING)
            return 0

        try:
            t = output.split()[0]
            return int(t)
        except (ValueError, IndexError):
            self.exception("failed to parse hg log output; using timestamp of 0 instead", level=WARNING)
            return 0

    def query_do_upload(self):
        # always upload nightlies, but not dep builds for some platforms
        if self.query_is_nightly():
            return True
        if self.config['target'] in self.config.get('upload_dep_target_exclusions', []):
            return False
        return True

    def query_build_env(self):
        """Retrieves the environment for building"""
        dirs = self.query_abs_dirs()
        gecko_config = self.load_gecko_config()
        env = self.query_env()
        env.update(gecko_config.get('env', {}))
        if self.config.get('variant'):
            v = str(self.config['variant'])
            env['VARIANT'] = v
        if self.config.get('ccache'):
            env['CCACHE_BASEDIR'] = dirs['work_dir']
        # If we get a buildid from buildbot, pass that in as MOZ_BUILD_DATE
        if self.buildbot_config and 'buildid' in self.buildbot_config.get('properties', {}):
            env['MOZ_BUILD_DATE'] = self.buildbot_config['properties']['buildid']

        return env

    # Actions {{{2
    def clobber(self):
        c = self.config
        if c.get('is_automation'):
            # Nightly builds always clobber
            do_clobber = False
            if self.query_is_nightly():
                self.info("Clobbering because we're a nightly build")
                do_clobber = True
            if c.get('force_clobber'):
                self.info("Clobbering because our config forced us to")
                do_clobber = True
            if do_clobber:
                super(B2GBuild, self).clobber()
            else:
                # Delete the upload dir so we don't upload previous stuff by accident
                dirs = self.query_abs_dirs()
                self.rmtree(dirs['abs_upload_dir'])
                self.rmtree(dirs['testdata_dir'])
            # run purge_builds / check clobberer
            self.purge_builds()
        else:
            super(B2GBuild, self).clobber()

    def checkout_gecko(self):
        '''
        If you want a different revision of gecko to be used you can use the
        --checkout-revision flag. This is necessary for trees that are not
        triggered by a gecko commit but by an external tree (like gaia).
        '''
        dirs = self.query_abs_dirs()

        # Make sure the parent directory to gecko exists so that 'hg share ...
        # build/gecko' works
        self.mkdir_p(os.path.dirname(dirs['src']))

        repo = self.query_repo()
        if "checkout_revision" in self.config:
            rev = self.vcs_checkout(repo=repo, dest=dirs['src'], revision=self.config["checkout_revision"])
            # in this case, self.query_revision() will be returning the "revision" that triggered the job
            # we know that it is not a gecko revision that did so
            self.set_buildbot_property('revision', self.query_revision(), write_to_file=True)
        else:
            # a gecko revision triggered this job; self.query_revision() will return it
            rev = self.vcs_checkout(repo=repo, dest=dirs['src'], revision=self.query_revision())
            self.set_buildbot_property('revision', rev, write_to_file=True)
        self.set_buildbot_property('gecko_revision', rev, write_to_file=True)

    def download_gonk(self):
        c = self.config
        dirs = self.query_abs_dirs()
        gonk_url = None
        if 'gonk_snapshot_url' in c:
            # We've overridden which gonk to use
            gonk_url = c['gonk_snapshot_url']
        else:
            gecko_config = self.load_gecko_config()
            if 'tooltool_manifest' in gecko_config:
                # The manifest is relative to the gecko config
                config_dir = os.path.join(dirs['src'], 'b2g', 'config',
                                          self.config.get('b2g_config_dir', self.config['target']))
                manifest = os.path.abspath(os.path.join(config_dir, gecko_config['tooltool_manifest']))
                self.tooltool_fetch(manifest, dirs['work_dir'])
                return
            gonk_url = gecko_config['gonk_snapshot_url']

        if gonk_url:
            if os.path.exists("gonk.tar.xz"):
                self.info("Skipping download of %s because we have a local copy already" % gonk_url)
            else:
                retval = self.download_file(gonk_url, os.path.join(dirs['work_dir'], 'gonk.tar.xz'))
                if retval is None:
                    self.fatal("failed to download gonk", exit_code=2)

    def unpack_gonk(self):
        dirs = self.query_abs_dirs()
        mtime = int(os.path.getmtime(os.path.join(dirs['abs_work_dir'], 'gonk.tar.xz')))
        mtime_file = os.path.join(dirs['abs_work_dir'], '.gonk_mtime')
        tar = self.query_exe('tar', return_type="list")
        if os.path.exists(mtime_file):
            try:
                prev_mtime = int(self.read_from_file(mtime_file, error_level=INFO))
                if mtime == prev_mtime:
                    # transition code - help existing build dirs without a sources.xml.original
                    sourcesfile = os.path.join(dirs['work_dir'], 'sources.xml')
                    sourcesfile_orig = sourcesfile + '.original'
                    if not os.path.exists(sourcesfile_orig):
                        self.run_command(tar + ["xf", "gonk.tar.xz", "--strip-components", "1", "B2G_default_*/sources.xml"],
                                         cwd=dirs['work_dir'])
                        self.run_command(["cp", "-p", sourcesfile, sourcesfile_orig], cwd=dirs['work_dir'])
                    # end transition code
                    self.info("We already have this gonk unpacked; skipping")
                    return
            except:
                pass
        if self.config.get('additional_source_tarballs'):
            for tarball in self.config['additional_source_tarballs']:
                self.run_command(tar + ["xf", tarball], cwd=dirs['work_dir'],
                                 halt_on_failure=True)

        retval = self.run_command(tar + ["xf", "gonk.tar.xz", "--strip-components", "1"], cwd=dirs['work_dir'])

        if retval != 0:
            self.fatal("failed to unpack gonk", exit_code=2)

        # output our sources.xml, make a copy for update_sources_xml()
        self.run_command(["cat", "sources.xml"], cwd=dirs['work_dir'])
        self.run_command(["cp", "-p", "sources.xml", "sources.xml.original"], cwd=dirs['work_dir'])

        self.info("Writing %s to %s" % (mtime, mtime_file))
        self.write_to_file(mtime_file, str(mtime))

    def checkout_gaia(self):
        dirs = self.query_abs_dirs()
        gecko_config = self.load_gecko_config()
        gaia_config = gecko_config.get('gaia')
        if gaia_config:
            dest = os.path.join(dirs['abs_work_dir'], 'gaia')
            repo = gaia_config['repo']
            branch = gaia_config.get('branch')
            vcs = gaia_config['vcs']
            rev = self.vcs_checkout(repo=repo, dest=dest, vcs=vcs, branch=branch)
            self.set_buildbot_property('gaia_revision', rev, write_to_file=True)
            self.info("TinderboxPrint: gaia_revlink: %s/rev/%s" % (repo, rev))

    def checkout_gaia_l10n(self):
        if not self.config.get('gaia_languages_file'):
            self.info('Skipping checkout_gaia_l10n because no gaia language file was specified.')
            return

        l10n_config = self.load_gecko_config().get('gaia', {}).get('l10n')
        if not l10n_config:
            self.fatal("gaia.l10n is required in the gecko config when --gaia-languages-file is specified.")

        abs_work_dir = self.query_abs_dirs()['abs_work_dir']
        languages_file = os.path.join(abs_work_dir, 'gaia', self.config['gaia_languages_file'])
        l10n_base_dir = self.query_abs_dirs()['gaia_l10n_base_dir']

        self.pull_gaia_locale_source(l10n_config, parse_config_file(languages_file).keys(), l10n_base_dir)

    def checkout_gecko_l10n(self):
        hg_l10n_base = self.load_gecko_config().get('gecko_l10n_root')
        self.pull_locale_source(hg_l10n_base=hg_l10n_base)
        gecko_locales = self.query_locales()
        # populate b2g/overrides, which isn't in gecko atm
        dirs = self.query_abs_dirs()
        for locale in gecko_locales:
            self.mkdir_p(os.path.join(dirs['abs_l10n_dir'], locale, 'b2g', 'chrome', 'overrides'))
            self.copytree(os.path.join(dirs['abs_l10n_dir'], locale, 'mobile', 'overrides'),
                          os.path.join(dirs['abs_l10n_dir'], locale, 'b2g', 'chrome', 'overrides'),
                          error_level=FATAL)

    def checkout_compare_locales(self):
        dirs = self.query_abs_dirs()
        dest = dirs['compare_locales_dir']
        repo = self.config['compare_locales_repo']
        rev = self.config['compare_locales_rev']
        vcs = self.config['compare_locales_vcs']
        abs_rev = self.vcs_checkout(repo=repo, dest=dest, revision=rev, vcs=vcs)
        self.set_buildbot_property('compare_locales_revision', abs_rev, write_to_file=True)

    def query_do_translate_hg_to_git(self, gecko_config_key=None):
        manifest_config = self.config.get('manifest', {})
        branch = self.query_branch()
        if self.query_is_nightly() and branch in manifest_config['branches'] and \
                manifest_config.get('translate_hg_to_git'):
            if gecko_config_key is None:
                return True
            if self.gecko_config.get(gecko_config_key):
                return True
        return False

    def _generate_git_locale_manifest(self, locale, url, git_repo,
                                      revision, git_base_url, local_path):
        l10n_git_sha = self.query_translated_revision(url, 'l10n', revision, project_name="l10n %s" % locale)
        return '  <project name="%s" path="%s" remote="mozillaorg" revision="%s"/>' % (git_repo.replace(git_base_url, ''), local_path, l10n_git_sha)

    def _generate_locale_manifest(self, git_base_url="https://git.mozilla.org/release/"):
        """ Add the locales to the source manifest.
        """
        manifest_config = self.config.get('manifest', {})
        locale_manifest = []
        if self.gaia_locale_revisions:
            gaia_l10n_git_root = None
            if self.query_do_translate_hg_to_git(gecko_config_key='gaia_l10n_git_root'):
                gaia_l10n_git_root = self.gecko_config['gaia_l10n_git_root']
            for locale in self.gaia_locale_revisions.keys():
                repo = self.gaia_locale_revisions[locale]['repo']
                revision = self.gaia_locale_revisions[locale]['revision']
                locale_manifest.append('  <!-- Mercurial-Information: <project name="%s" path="gaia-l10n/%s" remote="hgmozillaorg" revision="%s"/> -->' %
                                       (repo.replace('http://hg.mozilla.org/', ''), locale, revision))
                if gaia_l10n_git_root:
                    locale_manifest.append(
                        self._generate_git_locale_manifest(
                            locale,
                            manifest_config['translate_base_url'],
                            gaia_l10n_git_root % {'locale': locale},
                            revision,
                            git_base_url,
                            "gaia-l10n/%s" % locale,
                        )
                    )
        if self.gecko_locale_revisions:
            gecko_l10n_git_root = None
            if self.query_do_translate_hg_to_git(gecko_config_key='gecko_l10n_git_root'):
                gecko_l10n_git_root = self.gecko_config['gecko_l10n_git_root']
            for locale in self.gecko_locale_revisions.keys():
                repo = self.gecko_locale_revisions[locale]['repo']
                revision = self.gecko_locale_revisions[locale]['revision']
                locale_manifest.append('  <!-- Mercurial-Information: <project name="%s" path="gecko-l10n/%s" remote="hgmozillaorg" revision="%s"/> -->' %
                                       (repo.replace('http://hg.mozilla.org/', ''), locale, revision))
                if gecko_l10n_git_root:
                    locale_manifest.append(
                        self._generate_git_locale_manifest(
                            locale,
                            manifest_config['translate_base_url'],
                            gecko_l10n_git_root % {'locale': locale},
                            revision,
                            git_base_url,
                            "gecko-l10n/%s" % locale,
                        )
                    )
        return locale_manifest

    def update_source_manifest(self):
        dirs = self.query_abs_dirs()
        gecko_config = self.load_gecko_config()
        gaia_config = gecko_config.get('gaia')
        manifest_config = self.config.get('manifest', {})

        sourcesfile = os.path.join(dirs['work_dir'], 'sources.xml')
        sourcesfile_orig = sourcesfile + '.original'
        sources = self.read_from_file(sourcesfile_orig, verbose=False)
        dom = xml.dom.minidom.parseString(sources)
        git_base_url = "https://git.mozilla.org/"
        for element in dom.getElementsByTagName('remote'):
            if element.getAttribute('name') == 'mozillaorg':
                pieces = urlparse.urlparse(element.getAttribute('fetch'))
                if pieces:
                    git_base_url = "https://git.mozilla.org%s" % pieces[2]
                    if not git_base_url.endswith('/'):
                        git_base_url += "/"
                    self.info("Found git_base_url of %s in manifest." % git_base_url)
                    break
        else:
            self.warning("Couldn't find git_base_url in manifest; using %s" % git_base_url)
        new_sources = []

        for line in sources.splitlines():
            new_sources.append(line)
            if 'Gonk specific things' in line:
                new_sources.append('  <!-- Mercurial-Information: <remote fetch="http://hg.mozilla.org/" name="hgmozillaorg"> -->')
                new_sources.append('  <!-- Mercurial-Information: <project name="%s" path="gecko" remote="hgmozillaorg" revision="%s"/> -->' %
                                   (self.buildbot_config['properties']['repo_path'], self.buildbot_properties['gecko_revision']))
                new_sources.append('  <!-- Mercurial-Information: <project name="%s" path="gaia" remote="hgmozillaorg" revision="%s"/> -->' %
                                   (gaia_config['repo'].replace('http://hg.mozilla.org/', ''), self.buildbot_properties['gaia_revision']))

                if self.query_do_translate_hg_to_git():
                    url = manifest_config['translate_base_url']
                    gecko_git = self.query_translated_revision(url, 'gecko', self.buildbot_properties['gecko_revision'])
                    gaia_git = self.query_translated_revision(url, 'gaia', self.buildbot_properties['gaia_revision'])
                    new_sources.append('  <project name="%s" path="gecko" remote="mozillaorg" revision="%s"/>' % ("https://git.mozilla.org/releases/gecko.git".replace(git_base_url, ''), gecko_git))
                    new_sources.append('  <project name="%s" path="gaia" remote="mozillaorg" revision="%s"/>' % ("https://git.mozilla.org/releases/gaia.git".replace(git_base_url, ''), gaia_git))

                    # Figure out when our gaia commit happened
                    gaia_time = self.get_hg_commit_time(os.path.join(dirs['abs_work_dir'], 'gaia'), self.buildbot_properties['gaia_revision'])

                    # Write the gaia commit information to 'gaia_commit_override.txt'
                    gaia_override = os.path.join(dirs['abs_work_dir'], 'gaia', 'gaia_commit_override.txt')
                    self.write_to_file(gaia_override, "%s\n%s\n" % (gaia_git, gaia_time))
                new_sources.extend(self._generate_locale_manifest(git_base_url=git_base_url))

        self.write_to_file(sourcesfile, "\n".join(new_sources), verbose=False)
        self.run_command(["diff", "-u", sourcesfile_orig, sourcesfile], success_codes=[1])

    def build(self):
        dirs = self.query_abs_dirs()
        gecko_config = self.load_gecko_config()
        build_targets = gecko_config.get('build_targets', [])
        cmd = ['./build.sh'] + build_targets
        env = self.query_build_env()
        if self.config.get('gaia_languages_file'):
            env['LOCALE_BASEDIR'] = dirs['gaia_l10n_base_dir']
            env['LOCALES_FILE'] = os.path.join(dirs['abs_work_dir'], 'gaia', self.config['gaia_languages_file'])
        if self.config.get('locales_file'):
            env['L10NBASEDIR'] = dirs['abs_l10n_dir']
            env['MOZ_CHROME_MULTILOCALE'] = " ".join(self.locales)
            env['PATH'] = os.environ.get('PATH')
            env['PATH'] += ':%s' % os.path.join(dirs['compare_locales_dir'], 'scripts')
            env['PYTHONPATH'] = os.environ.get('PYTHONPATH', '')
            env['PYTHONPATH'] += ':%s' % os.path.join(dirs['compare_locales_dir'], 'lib')

        # Write .userconfig to point to the correct object directory for gecko
        # Normally this is embedded inside the .config file included with the snapshot
        self.write_to_file(
            os.path.join(dirs['work_dir'], '.userconfig'),
            "GECKO_OBJDIR=%s\n" % self.objdir)

        if 'mock_target' in gecko_config:
            # initialize mock
            self.setup_mock(gecko_config['mock_target'], gecko_config['mock_packages'], gecko_config.get('mock_files'))
            if self.config['ccache']:
                self.run_mock_command(gecko_config['mock_target'], 'ccache -z', cwd=dirs['work_dir'], env=env)

            retval = self.run_mock_command(gecko_config['mock_target'], cmd, cwd=dirs['work_dir'], env=env, error_list=B2GMakefileErrorList)
            if self.config['ccache']:
                self.run_mock_command(gecko_config['mock_target'], 'ccache -s', cwd=dirs['work_dir'], env=env)
        else:
            if self.config['ccache']:
                self.run_command('ccache -z', cwd=dirs['work_dir'], env=env)
            retval = self.run_command(cmd, cwd=dirs['work_dir'], env=env, error_list=B2GMakefileErrorList)
            if self.config['ccache']:
                self.run_command('ccache -s', cwd=dirs['work_dir'], env=env)

        if retval != 0:
            self.fatal("failed to build", exit_code=2)

        buildid = self.query_buildid()
        self.set_buildbot_property('buildid', buildid, write_to_file=True)

    def build_symbols(self):
        dirs = self.query_abs_dirs()
        gecko_config = self.load_gecko_config()
        if gecko_config.get('config_version', 0) < 1:
            self.info("Skipping build_symbols for old configuration")
            return

        cmd = ['./build.sh', 'buildsymbols']
        env = self.query_build_env()

        # Write .userconfig to point to the correct object directory for gecko
        # Normally this is embedded inside the .config file included with the snapshot
        self.write_to_file(
            os.path.join(dirs['work_dir'], '.userconfig'),
            "GECKO_OBJDIR=%s\n" % self.objdir)

        if 'mock_target' in gecko_config:
            # initialize mock
            self.setup_mock(gecko_config['mock_target'], gecko_config['mock_packages'], gecko_config.get('mock_files'))
            retval = self.run_mock_command(gecko_config['mock_target'], cmd, cwd=dirs['work_dir'], env=env, error_list=B2GMakefileErrorList)
        else:
            retval = self.run_command(cmd, cwd=dirs['work_dir'], env=env, error_list=B2GMakefileErrorList)

        if retval != 0:
            self.fatal("failed to build symbols", exit_code=2)

        if self.query_is_nightly():
            # Upload symbols
            self.info("Uploading symbols")
            cmd = ['./build.sh', 'uploadsymbols']
            if 'mock_target' in gecko_config:
                retval = self.run_mock_command(gecko_config['mock_target'], cmd, cwd=dirs['work_dir'], env=env, error_list=B2GMakefileErrorList)
            else:
                retval = self.run_command(cmd, cwd=dirs['work_dir'], env=env, error_list=B2GMakefileErrorList)

            if retval != 0:
                self.fatal("failed to upload symbols", exit_code=2)

    def make_updates(self):
        if not self.query_is_nightly():
            self.info("Not a nightly build. Skipping...")
            return
        dirs = self.query_abs_dirs()
        gecko_config = self.load_gecko_config()
        cmd = ['./build.sh', 'gecko-update-full']
        env = self.query_build_env()

        # Write .userconfig to point to the correct object directory for gecko
        # Normally this is embedded inside the .config file included with the snapshot
        # TODO: factor this out so it doesn't get run twice
        self.write_to_file(
            os.path.join(dirs['work_dir'], '.userconfig'),
            "GECKO_OBJDIR=%s\n" % self.objdir)

        if 'mock_target' in gecko_config:
            # initialize mock
            self.setup_mock(gecko_config['mock_target'], gecko_config['mock_packages'], gecko_config.get('mock_files'))
            retval = self.run_mock_command(gecko_config['mock_target'], cmd, cwd=dirs['work_dir'], env=env, error_list=B2GMakefileErrorList)
        else:
            retval = self.run_command(cmd, cwd=dirs['work_dir'], env=env, error_list=B2GMakefileErrorList)

        if retval != 0:
            self.fatal("failed to create complete update", exit_code=2)

        # Sign the updates
        self.sign_updates()

    def build_update_testdata(self):
        # only run for nightlies, if target is in the smoketest_config
        if not self.query_is_nightly():
            self.info("Not a nightly build. Skipping...")
            return
        smoketest_config = self.config.get('smoketest_config')
        if not smoketest_config:
            self.fatal("failed to find smoketest_config")
        target = self.config['target']
        if target not in smoketest_config['devices']:
            self.info("%s not in smoketest_config. Skipping...")
            return

        # create testdata for update testing
        dirs = self.query_abs_dirs()
        gecko_config = self.load_gecko_config()
        cmd = ['./build.sh', 'fs_config']
        env = self.query_build_env()

        retval = self.run_mock_command(gecko_config['mock_target'], cmd, cwd=dirs['work_dir'], env=env, error_list=B2GMakefileErrorList)
        if retval != 0:
            self.fatal("failed to build fs_config", exit_code=2)

        self.mkdir_p(dirs['testdata_dir'])
        self.write_to_file(os.path.join(dirs['testdata_dir'], 'smoketest-config.json'),
                           json.dumps(smoketest_config))
        gecko_smoketest_dir = os.path.join(dirs['work_dir'], 'gecko/testing/marionette/update-smoketests')

        stage_update = os.path.join(gecko_smoketest_dir, 'stage-update.py')
        python = self.query_exe("python", return_type="list")
        cmd = python + [stage_update, target, dirs['testdata_dir']]
        retval = self.run_mock_command(gecko_config['mock_target'], cmd, cwd=dirs['work_dir'], env=env)
        if retval != 0:
            self.fatal("failed to stage b2g update testdata", exit_code=2)

        # copy to upload_dir
        buildid = self.query_buildid()
        upload_testdata_dir = os.path.join(dirs['abs_upload_dir'], 'update-testdata')
        target_testdata_dir = os.path.join(dirs['testdata_dir'], target, buildid)
        self.mkdir_p(upload_testdata_dir)

        for f in ('flash.zip', 'flash.sh'):
            self.copy_to_upload_dir(
                os.path.join(target_testdata_dir, f),
                os.path.join(upload_testdata_dir, f))

    def sign_updates(self):
        if 'MOZ_SIGNING_SERVERS' not in os.environ:
            self.info("Skipping signing since no MOZ_SIGNING_SERVERS set")
            return

        dirs = self.query_abs_dirs()

        # We need hg.m.o/build/tools checked out
        self.info("Checking out tools")
        repos = [{
            'repo': self.config['tools_repo'],
            'vcs': "hgtool",
            'dest': os.path.join(dirs['abs_work_dir'], "tools")
        }]
        rev = self.vcs_checkout(**repos[0])
        self.set_buildbot_property("tools_revision", rev, write_to_file=True)

        cmd = self.query_moz_sign_cmd(formats='b2gmar')
        cmd.append(self.marfile)

        retval = self.run_command(cmd)
        if retval != 0:
            self.fatal("failed to sign complete update", exit_code=2)

    def prep_upload(self):
        if not self.query_do_upload():
            self.info("Uploads disabled for this build. Skipping...")
            return

        dirs = self.query_abs_dirs()

        # Copy stuff into build/upload directory
        gecko_config = self.load_gecko_config()

        output_dir = os.path.join(dirs['work_dir'], 'out', 'target', 'product', self.config['target'])

        # Zip up stuff
        files = []
        for item in gecko_config.get('zip_files', []):
            if isinstance(item, list):
                pattern, target = item
            else:
                pattern, target = item, None

            pattern = pattern.format(objdir=self.objdir, workdir=dirs['work_dir'], srcdir=dirs['src'])
            for f in glob.glob(pattern):
                files.append((f, target))

        if files:
            zip_name = os.path.join(dirs['work_dir'], self.config['target'] + ".zip")
            self.info("creating %s" % zip_name)
            tmpdir = tempfile.mkdtemp()
            try:
                zip_dir = os.path.join(tmpdir, 'b2g-distro')
                self.mkdir_p(zip_dir)
                for f, target in files:
                    if target is None:
                        dst = os.path.join(zip_dir, os.path.basename(f))
                    elif target.endswith('/'):
                        dst = os.path.join(zip_dir, target, os.path.basename(f))
                    else:
                        dst = os.path.join(zip_dir, target)
                    if not os.path.exists(os.path.dirname(dst)):
                        self.mkdir_p(os.path.dirname(dst))
                    self.copyfile(f, dst, copystat=True)

                cmd = ['zip', '-r', '-9', '-u', zip_name, 'b2g-distro']
                if self.run_command(cmd, cwd=tmpdir) != 0:
                    self.fatal("problem zipping up files")
                self.copy_to_upload_dir(zip_name)
            finally:
                self.debug("removing %s" % tmpdir)
                self.rmtree(tmpdir)

        self.info("copying files to upload directory")
        files = []

        files.append(os.path.join(output_dir, 'system', 'build.prop'))

        for pattern in gecko_config.get('upload_files', []):
            pattern = pattern.format(objdir=self.objdir, workdir=dirs['work_dir'], srcdir=dirs['src'])
            for f in glob.glob(pattern):
                files.append(f)

        for f in files:
            if f.endswith(".img"):
                if self.query_is_nightly():
                    # Compress it
                    self.info("compressing %s" % f)
                    self.run_command(["bzip2", f])
                    f += ".bz2"
                else:
                    # Skip it
                    self.info("not uploading %s for non-nightly build" % f)
                    continue
            self.info("copying %s to upload directory" % f)
            self.copy_to_upload_dir(f)

        self.copy_logs_to_upload_dir()

    def upload(self):
        if not self.query_do_upload():
            self.info("Uploads disabled for this build. Skipping...")
            return

        dirs = self.query_abs_dirs()
        c = self.config
        target = self.load_gecko_config().get('upload_platform', self.config['target'])
        if c.get("target_suffix"):
            target += c["target_suffix"]
        if c['enable_try_uploads']:
            try:
                user = self.buildbot_config['sourcestamp']['changes'][0]['who']
            except KeyError:
                user = "unknown"
            upload_path = "%(basepath)s/%(user)s-%(rev)s/%(branch)s-%(target)s" % dict(
                basepath=self.config['upload_remote_basepath'],
                branch=self.query_branch(),
                target=target,
                user=user,
                rev=self.query_revision(),
            )
        elif self.query_is_nightly():
            # Dates should be based on buildid
            buildid = self.query_buildid()
            if buildid:
                try:
                    buildid = datetime.strptime(buildid, "%Y%m%d%H%M%S")
                except ValueError:
                    buildid = None

            if buildid is None:
                # Default to now
                buildid = datetime.now()

            upload_path = "%(basepath)s/%(branch)s-%(target)s/%(year)04i/%(month)02i/%(year)04i-%(month)02i-%(day)02i-%(hour)02i-%(minute)02i-%(second)02i" % dict(
                basepath=self.config['upload_remote_nightly_basepath'],
                branch=self.query_branch(),
                target=target,
                year=buildid.year,
                month=buildid.month,
                day=buildid.day,
                hour=buildid.hour,
                minute=buildid.minute,
                second=buildid.second,
            )
        else:
            upload_path = "%(basepath)s/%(branch)s-%(target)s/%(buildid)s" % dict(
                basepath=self.config['upload_remote_basepath'],
                branch=self.query_branch(),
                buildid=self.query_buildid(),
                target=target,
            )

        retval = self.rsync_upload_directory(
            dirs['abs_upload_dir'],
            self.config['ssh_key'],
            self.config['ssh_user'],
            self.config['upload_remote_host'],
            upload_path,
        )

        if retval is not None:
            self.error("failed to upload")
            self.return_code = 2
        else:
            upload_url = "http://%(upload_remote_host)s/%(upload_path)s" % dict(
                upload_remote_host=self.config['upload_remote_host'],
                upload_path=upload_path,
            )
            download_url = "http://pvtbuilds.pvt.build.mozilla.org/%(upload_path)s" % dict(
                upload_path=upload_path,
            )

            self.info("Upload successful: %s" % upload_url)

            if self.query_is_nightly():
                # Create a symlink to the latest nightly
                symlink_path = "%(basepath)s/%(branch)s-%(target)s/latest" % dict(
                    basepath=self.config['upload_remote_nightly_basepath'],
                    branch=self.query_branch(),
                    target=target,
                )

                ssh = self.query_exe('ssh')
                # First delete the symlink if it exists
                cmd = [ssh,
                       '-l', self.config['ssh_user'],
                       '-i', self.config['ssh_key'],
                       self.config['upload_remote_host'],
                       'rm -f %s' % symlink_path,
                       ]
                retval = self.run_command(cmd)
                if retval != 0:
                    self.error("failed to delete latest symlink")
                    self.return_code = 2
                # Now create the symlink
                rel_path = os.path.relpath(upload_path, os.path.dirname(symlink_path))
                cmd = [ssh,
                       '-l', self.config['ssh_user'],
                       '-i', self.config['ssh_key'],
                       self.config['upload_remote_host'],
                       'ln -sf %s %s' % (rel_path, symlink_path),
                       ]
                retval = self.run_command(cmd)
                if retval != 0:
                    self.error("failed to create latest symlink")
                    self.return_code = 2

            if self.config["target"] == "panda" and self.config.get('sendchange_masters'):
                self.sendchange(downloadables=[download_url, "%s/%s" % (download_url, "gaia-tests.zip")])

    def make_socorro_json(self):
        self.info("Creating socorro.json...")
        dirs = self.query_abs_dirs()
        manifest_config = self.config.get('manifest', {})
        socorro_dict = {
            'buildid': self.query_buildid(),
            'version': self.query_version(),
            'update_channel': manifest_config.get('update_channel'),
            #'beta_number': n/a until we build b2g beta releases
        }
        file_path = os.path.join(dirs['abs_work_dir'], 'socorro.json')
        fh = open(file_path, 'w')
        json.dump(socorro_dict, fh)
        fh.close()
        self.run_command(["cat", file_path])

    def upload_source_manifest(self):
        if not self.query_is_nightly():
            self.info("Not a nightly build. Skipping...")
            return
        manifest_config = self.config.get('manifest')
        branch = self.query_branch()
        if not manifest_config or not branch:
            self.info("No manifest config or can't get branch from build. Skipping...")
            return
        if branch not in manifest_config['branches']:
            self.info("Manifest upload not enabled for this branch. Skipping...")
            return
        version = manifest_config['branches'][branch]
        upload_remote_basepath = self.config['manifest']['upload_remote_basepath'] % {'version': version}

        dirs = self.query_abs_dirs()
        upload_dir = dirs['abs_upload_dir'] + '-manifest'
        # Delete the upload dir so we don't upload previous stuff by accident
        self.rmtree(upload_dir)

        # Dates should be based on buildid
        buildid = self.query_buildid()
        if buildid:
            try:
                buildid = datetime.strptime(buildid, "%Y%m%d%H%M%S")
            except ValueError:
                buildid = None

        if buildid is None:
            # Default to now
            buildid = datetime.now()

        target = self.config['target']
        if self.config['manifest'].get('target_suffix'):
            target += self.config['manifest']['target_suffix']
        # emulator builds will disappear out of latest/ because they're once-daily
        date_string = '%(year)04i-%(month)02i-%(day)02i-%(hour)02i' % dict(
            year=buildid.year,
            month=buildid.month,
            day=buildid.day,
            hour=buildid.hour,
        )
        xmlfilename = 'source_%(target)s_%(date_string)s.xml' % dict(
            target=target,
            date_string=date_string,
        )
        self.copy_to_upload_dir(
            os.path.join(dirs['work_dir'], 'sources.xml'),
            os.path.join(upload_dir, xmlfilename)
        )
        socorro_json = os.path.join(dirs['work_dir'], 'socorro.json')
        socorro_filename = 'socorro_%(target)s_%(date_string)s.json' % dict(
            target=target,
            date_string=date_string,
        )
        if os.path.exists(socorro_json):
            self.copy_to_upload_dir(
                socorro_json,
                os.path.join(upload_dir, socorro_filename)
            )
        retval = self.rsync_upload_directory(
            upload_dir,
            self.config['manifest']['ssh_key'],
            self.config['manifest']['ssh_user'],
            self.config['manifest']['upload_remote_host'],
            upload_remote_basepath,
        )
        if retval is not None:
            self.error("Failed to upload")
            self.return_code = 2

        # run jgriffin's orgranize.py to shuffle the files around
        # https://github.com/jonallengriffin/b2gautomation/blob/master/b2gautomation/organize.py
        ssh = self.query_exe('ssh')
        cmd = [ssh,
               '-l', self.config['manifest']['ssh_user'],
               '-i', self.config['manifest']['ssh_key'],
               self.config['manifest']['upload_remote_host'],
               'python ~/organize.py --directory %s' % upload_remote_basepath,
               ]
        retval = self.run_command(cmd)
        if retval != 0:
            self.error("Failed to move manifest to final location")
            self.return_code = 2
        else:
            self.info("Upload successful")

    def make_update_xml(self):
        if not self.query_is_nightly():
            self.info("Not a nightly build. Skipping...")
            return
        if not self.config.get('update'):
            self.info("No updates. Skipping...")
            return

        dirs = self.query_abs_dirs()
        upload_dir = dirs['abs_upload_dir'] + '-updates'
        # Delete the upload dir so we don't upload previous stuff by accident
        self.rmtree(upload_dir)

        suffix = self.query_buildid()
        dated_mar = "b2g_update_%s.mar" % suffix
        dated_update_xml = "update_%s.xml" % suffix
        dated_application_ini = "application_%s.ini" % suffix
        dated_sources_xml = "b2g_update_source_%s.xml" % suffix
        mar_url = self.config['update']['base_url'] + dated_mar

        self.info("Generating update.xml for %s" % mar_url)
        if not self.create_update_xml(self.marfile, self.query_version(),
                                      self.query_buildid(),
                                      mar_url,
                                      upload_dir):
            self.fatal("Failed to generate update.xml")

        self.copy_to_upload_dir(
            self.marfile,
            os.path.join(upload_dir, dated_mar)
        )
        self.copy_to_upload_dir(
            self.application_ini,
            os.path.join(upload_dir, dated_application_ini)
        )
        # copy update.xml to update_${buildid}.xml to keep history of updates
        self.copy_to_upload_dir(
            os.path.join(upload_dir, "update.xml"),
            os.path.join(upload_dir, dated_update_xml)
        )
        self.copy_to_upload_dir(
            os.path.join(dirs['work_dir'], 'sources.xml'),
            os.path.join(upload_dir, dated_sources_xml)
        )

    def upload_updates(self):
        if not self.query_is_nightly():
            self.info("Not a nightly build. Skipping...")
            return
        if not self.config.get('update'):
            self.info("No updates. Skipping...")
            return
        dirs = self.query_abs_dirs()
        upload_dir = dirs['abs_upload_dir'] + '-updates'
        # upload dated files first to be sure that update.xml doesn't
        # point to not existing files
        retval = self.rsync_upload_directory(
            upload_dir,
            self.config['update']['ssh_key'],
            self.config['update']['ssh_user'],
            self.config['update']['upload_remote_host'],
            self.config['update']['upload_remote_basepath'],
            rsync_options=['-azv', "--exclude=update.xml"]
        )
        if retval is not None:
            self.error("failed to upload")
            self.return_code = 2
        else:
            self.info("Upload successful")

        if self.config['update'].get('autopublish'):
            # rsync everything, including update.xml
            retval = self.rsync_upload_directory(
                upload_dir,
                self.config['update']['ssh_key'],
                self.config['update']['ssh_user'],
                self.config['update']['upload_remote_host'],
                self.config['update']['upload_remote_basepath'],
            )

            if retval is not None:
                self.error("failed to upload")
                self.return_code = 2
            else:
                self.info("Upload successful")


# main {{{1
if __name__ == '__main__':
    myScript = B2GBuild()
    myScript.run()
