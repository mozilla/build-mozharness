#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import sys
import os
import glob
import re
import tempfile
from datetime import datetime
import urlparse
import xml.dom.minidom
import functools

try:
    import simplejson as json
    assert json
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
from mozharness.mozilla.repo_manifest import (load_manifest, rewrite_remotes,
                                              remove_project, get_project,
                                              get_remote, map_remote)
from mozharness.mozilla.mapper import MapperMixin

# B2G builds complain about java...but it doesn't seem to be a problem
# Let's turn those into WARNINGS instead
B2GMakefileErrorList = MakefileErrorList + [
    {'substr': r'''NS_ERROR_FILE_ALREADY_EXISTS: Component returned failure code''', 'level': ERROR},
]
B2GMakefileErrorList.insert(0, {'substr': r'/bin/bash: java: command not found', 'level': WARNING})


class B2GBuild(LocalesMixin, MockMixin, PurgeMixin, BaseScript, VCSMixin,
               TooltoolMixin, TransferMixin, BuildbotMixin, GaiaLocalesMixin,
               SigningMixin, MapperMixin):
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
        [["--update-channel"], {
            "dest": "update_channel",
            "help": "b2g update channel",
        }],
        [["--nightly-update-channel"], {
            "dest": "nightly_update_channel",
            "help": "b2g update channel for nightly builds",
        }],
        [["--publish-channel"], {
            "dest": "publish_channel",
            "help": "channel where build is published to",
        }],
        [["--debug"], {
            "dest": "debug_build",
            "action": "store_true",
            "help": "Set B2G_DEBUG=1 (debug build)",
        }],
    ]

    def __init__(self, require_config_file=False):
        self.gecko_config = None
        self.buildid = None
        self.wrote_b2g_config = False
        LocalesMixin.__init__(self)
        BaseScript.__init__(self,
                            config_options=self.config_options,
                            all_actions=[
                                'clobber',
                                'checkout-sources',
                                # Deprecated
                                'checkout-gecko',
                                'download-gonk',
                                'unpack-gonk',
                                'checkout-gaia',
                                'checkout-gaia-l10n',
                                'checkout-gecko-l10n',
                                'checkout-compare-locales',
                                # End deprecated
                                'get-blobs',
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
                                'checkout-sources',
                                'get-blobs',
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
                                'repo_repo': "https://git.mozilla.org/external/google/gerrit/git-repo.git",
                                'repo_remote_mappings': {},
                                'update_channel': 'default',
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
            'abs_public_upload_dir': os.path.join(abs_dirs['abs_work_dir'], 'upload-public'),
        }

        abs_dirs.update(dirs)
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def query_gecko_config_path(self):
        conf_file = self.config.get('gecko_config')
        if conf_file is None:
            conf_file = os.path.join(
                'b2g', 'config',
                self.config.get('b2g_config_dir', self.config['target']),
                'config.json'
            )
        return conf_file

    def load_gecko_config(self):
        if self.gecko_config:
            return self.gecko_config

        if 'gecko_config' not in self.config:
            # Grab from the remote if we're not overriding on the cmdline
            self.gecko_config = self.query_remote_gecko_config()
            return self.gecko_config

        dirs = self.query_abs_dirs()
        conf_file = self.query_gecko_config_path()
        if not os.path.isabs(conf_file):
            conf_file = os.path.abspath(os.path.join(dirs['src'], conf_file))

        if os.path.exists(conf_file):
            self.info("gecko_config file: %s" % conf_file)
            self.run_command(['cat', conf_file])
            self.gecko_config = json.load(open(conf_file))
            return self.gecko_config

        # The file doesn't exist; let's try loading it remotely
        self.gecko_config = self.query_remote_gecko_config()
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

    def query_b2g_version(self):
        manifest_config = self.config.get('manifest')
        branch = self.query_branch()
        if not manifest_config or not branch:
            return 'default'
        if branch not in manifest_config['branches']:
            return 'default'
        version = manifest_config['branches'][branch]
        return version

    def query_update_channel(self):
        if self.query_is_nightly() and 'nightly_update_channel' in self.config:
            return self.config['nightly_update_channel']
        else:
            return self.config['update_channel']

    def query_revision(self):
        if 'revision' in self.buildbot_properties:
            return self.buildbot_properties['revision']

        if self.buildbot_config and 'sourcestamp' in self.buildbot_config:
            return self.buildbot_config['sourcestamp']['revision']

        return None

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
        if self.config['target'] in self.config['upload']['default'].get('upload_dep_target_exclusions', []):
            return False
        return True

    def query_build_env(self):
        """Retrieves the environment for building"""
        dirs = self.query_abs_dirs()
        gecko_config = self.load_gecko_config()
        env = self.query_env()
        for k, v in gecko_config.get('env', {}).items():
            v = v.format(workdir=dirs['abs_work_dir'],
                         srcdir=os.path.abspath(dirs['src']))
            env[k] = v
        if self.config.get('variant'):
            v = str(self.config['variant'])
            env['VARIANT'] = v
        if self.config.get('ccache'):
            env['CCACHE_BASEDIR'] = dirs['work_dir']
        # If we get a buildid from buildbot, pass that in as MOZ_BUILD_DATE
        if self.buildbot_config and 'buildid' in self.buildbot_config.get('properties', {}):
            env['MOZ_BUILD_DATE'] = self.buildbot_config['properties']['buildid']

        if 'B2G_UPDATE_CHANNEL' not in env:
            env['B2G_UPDATE_CHANNEL'] = "{target}/{version}/{channel}".format(
                target=self.config['target'],
                channel=self.query_update_channel(),
                version=self.query_b2g_version(),
            )
        if self.config.get('debug_build'):
            env['B2G_DEBUG'] = '1'
        return env

    def query_hgweb_url(self, repo, rev, filename=None):
        if filename:
            url = "{baseurl}/raw-file/{rev}/{filename}".format(
                baseurl=repo,
                rev=rev,
                filename=filename)
        else:
            url = "{baseurl}/rev/{rev}".format(
                baseurl=repo,
                rev=rev)
        return url

    def query_gitweb_url(self, repo, rev, filename=None):
        bits = urlparse.urlparse(repo)
        repo = bits.path.lstrip('/')
        if filename:
            url = "{scheme}://{host}/?p={repo};a=blob;f={filename};h={rev}".format(
                scheme=bits.scheme,
                host=bits.netloc,
                repo=repo,
                filename=filename,
                rev=rev)
        else:
            url = "{scheme}://{host}/?p={repo};a=tree;h={rev}".format(
                scheme=bits.scheme,
                host=bits.netloc,
                repo=repo,
                rev=rev)
        return url

    def query_remote_gecko_config(self):
        repo = self.query_repo()
        # TODO: Hardcoding this sucks
        if 'hg.mozilla.org' in repo:
            rev = self.query_revision()
            if rev is None:
                rev = 'default'

            config_path = self.query_gecko_config_path()
            # Handle local files vs. in-repo files
            url = self.query_hgweb_url(repo, rev, config_path)
            return self.retry(self.load_json_from_url, args=(url,))

    # Actions {{{2
    def clobber(self):
        dirs = self.query_abs_dirs()
        PurgeMixin.clobber(
            self,
            always_clobber_dirs=[
                dirs['abs_upload_dir'],
                dirs['abs_public_upload_dir'],
                dirs['testdata_dir'],
            ],
        )

    def checkout_sources(self):
        dirs = self.query_abs_dirs()
        gecko_config = self.load_gecko_config()
        b2g_manifest_intree = gecko_config.get('b2g_manifest_intree')

        if gecko_config.get('config_version') >= 2:
            repos = [
                {'vcs': 'gittool', 'repo': 'https://git.mozilla.org/b2g/B2G.git', 'dest': dirs['work_dir']},
            ]

            if b2g_manifest_intree:
                # Checkout top-level B2G repo now
                self.vcs_checkout_repos(repos)
                b2g_manifest_branch = 'master'

                # Now checkout gecko inside the build directory
                self.checkout_gecko()
                conf_dir = os.path.join(dirs['src'], os.path.dirname(self.query_gecko_config_path()))
                manifest_filename = os.path.join(conf_dir, 'sources.xml')
                self.info("Using manifest at %s" % manifest_filename)
                have_gecko = True
            else:
                # Checkout B2G and b2g-manifests. We'll do gecko later
                b2g_manifest_branch = gecko_config.get('b2g_manifest_branch', 'master')
                repos.append(
                    {'vcs': 'gittool', 'repo': 'https://git.mozilla.org/b2g/b2g-manifest.git', 'dest': os.path.join(dirs['work_dir'], 'b2g-manifest'), 'branch': b2g_manifest_branch},
                )
                manifest_filename = gecko_config.get('b2g_manifest', self.config['target'] + '.xml')
                manifest_filename = os.path.join(dirs['work_dir'], 'b2g-manifest', manifest_filename)
                self.vcs_checkout_repos(repos)
                have_gecko = False

            manifest = load_manifest(manifest_filename)

            if not b2g_manifest_intree:
                # Now munge the manifest by mapping remotes to local remotes
                mapping_func = functools.partial(map_remote, mappings=self.config['repo_remote_mappings'])

                rewrite_remotes(manifest, mapping_func)
                # Remove gecko, since we'll be checking that out ourselves
                gecko_node = remove_project(manifest, path='gecko')
                if not gecko_node:
                    self.fatal("couldn't remove gecko from manifest")

            # repo requires a git repo to work with
            # so we create a temporary repo, put our manifest file into it, and
            # commit it
            manifest_dir = os.path.join(dirs['work_dir'], 'tmp_manifest')
            self.rmtree(manifest_dir)
            self.mkdir_p(manifest_dir)

            self.info("Writing manifest to %s" % manifest_filename)
            manifest_filename = os.path.join(manifest_dir, self.config['target'] + '.xml')
            manifest_file = open(manifest_filename, 'w')
            manifest.writexml(manifest_file)
            manifest_file.close()

            git = self.query_exe('git')
            self.run_command([git, 'init'], cwd=manifest_dir, halt_on_failure=True)
            self.run_command([git, 'add', manifest_filename], cwd=manifest_dir, halt_on_failure=True)
            self.run_command([git, 'commit', '-m', 'manifest'], cwd=manifest_dir, halt_on_failure=True)
            self.run_command([git, 'branch', '-m', b2g_manifest_branch], cwd=manifest_dir, halt_on_failure=True)

            # We need to reset gaia, since the build process locally modifies
            # files here, which can break sync later. \o/
            gaia_dir = os.path.join(dirs['work_dir'], 'gaia')
            if os.path.exists(gaia_dir):
                self.run_command([git, 'reset', '--hard'], cwd=gaia_dir)

            repo_repo = self.config['repo_repo']

            # Check it out!
            repo = os.path.join(dirs['work_dir'], 'repo')
            if 'repo_mirror_dir' in self.config:
                # Make our local .repo directory a symlink to the shared repo
                # directory
                repo_mirror_dir = self.config['repo_mirror_dir']
                self.mkdir_p(repo_mirror_dir)
                repo_link = os.path.join(dirs['work_dir'], '.repo')
                if not os.path.exists(repo_link) or not os.path.islink(repo_link):
                    self.rmtree(repo_link)
                    self.info("Creating link from %s to %s" % (repo_link, repo_mirror_dir))
                    os.symlink(repo_mirror_dir, repo_link)

            self.run_command([
                repo, "init", "--repo-url", repo_repo,
                # Bug 922750 - use --no-repo-verify to work around busted
                # upstream tagging
                "--no-repo-verify",
                "-q", "-u", manifest_dir,
                "-m", self.config['target'] + '.xml',
                '-b', b2g_manifest_branch],
                cwd=dirs['work_dir'], halt_on_failure=True)
            # self.run_command([repo, "sync", "--quiet"], cwd=dirs['work_dir'], halt_on_failure=True)
            # XXX Workaround git failing to clone some repositories when
            # running in quiet mode. See bug 857158
            self.run_command(['script', '-q', '-c', '%s sync' % repo], cwd=dirs['work_dir'], halt_on_failure=True)

            # output our sources.xml, make a copy for update_sources_xml()
            self.run_command(["./gonk-misc/add-revision.py", "-o", "sources.xml", "--force", ".repo/manifest.xml"], cwd=dirs["work_dir"], halt_on_failure=True)
            self.run_command(["cat", "sources.xml"], cwd=dirs['work_dir'], halt_on_failure=True)
            self.run_command(["cp", "-p", "sources.xml", "sources.xml.original"], cwd=dirs['work_dir'], halt_on_failure=True)

            manifest = load_manifest(os.path.join(dirs['work_dir'], 'sources.xml'))
            gaia_node = get_project(manifest, path="gaia")
            gaia_rev = gaia_node.getAttribute("revision")
            gaia_remote = get_remote(manifest, gaia_node.getAttribute('remote'))
            gaia_repo = "%s/%s" % (gaia_remote.getAttribute('fetch'), gaia_node.getAttribute('name'))
            gaia_url = self.query_gitweb_url(gaia_repo, gaia_rev)
            self.set_buildbot_property("gaia_revision", gaia_rev, write_to_file=True)
            self.info("TinderboxPrint: gaia_revlink: %s" % gaia_url)

            # Now we can checkout gecko and other stuff
            if not have_gecko:
                self.checkout_gecko()
            self.checkout_gecko_l10n()
            self.checkout_gaia_l10n()
            self.checkout_compare_locales()
            return

        # Old behaviour
        self.checkout_gecko()
        self.checkout_gaia()
        self.checkout_gaia_l10n()
        self.checkout_gecko_l10n()
        self.checkout_compare_locales()

    def get_blobs(self):
        self.download_blobs()
        self.unpack_blobs()

    def write_b2g_config(self):
        if self.wrote_b2g_config:
            return

        dirs = self.query_abs_dirs()

        # Write .config to point to the correct object directory for gecko
        # and specifies which target to use
        device_name = self.config['target']
        device = {
            'pandaboard': 'panda',
        }.get(device_name, device_name)

        # TODO: this re-implements some config.sh logic
        # TODO: write to .userconfig if we're using snapshots
        lines = [
            "GECKO_OBJDIR=%s" % self.objdir,
            "DEVICE_NAME=%s" % device_name,
            "DEVICE=%s" % device,
        ]
        # TODO: eh? what's this for? config.sh does it, but why?
        if device_name == 'generic':
            lines.append("LUNCH=full-eng")

        # Make sure we get a blank line at the end
        lines.append("")

        self.write_to_file(
            os.path.join(dirs['work_dir'], '.config'),
            "\n".join(lines)
        )

        self.wrote_b2g_config = True

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

    def download_blobs(self):
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
                self.tooltool_fetch(manifest=manifest,
                                    bootstrap_cmd=gecko_config.get('tooltool_bootstrap_cmd'),
                                    output_dir=dirs['work_dir'])
                return
            gonk_url = gecko_config['gonk_snapshot_url']

        if gonk_url:
            if os.path.exists("gonk.tar.xz"):
                self.info("Skipping download of %s because we have a local copy already" % gonk_url)
            else:
                retval = self.download_file(gonk_url, os.path.join(dirs['work_dir'], 'gonk.tar.xz'))
                if retval is None:
                    self.fatal("failed to download gonk", exit_code=2)

    def unpack_blobs(self):
        dirs = self.query_abs_dirs()
        tar = self.query_exe('tar', return_type="list")
        gonk_snapshot = os.path.join(dirs['abs_work_dir'], 'gonk.tar.xz')
        if os.path.exists(gonk_snapshot):
            mtime = int(os.path.getmtime(gonk_snapshot))
            mtime_file = os.path.join(dirs['abs_work_dir'], '.gonk_mtime')
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

            self.info("Writing %s to %s" % (mtime, mtime_file))
            self.write_to_file(mtime_file, str(mtime))
            retval = self.run_command(tar + ["xf", "gonk.tar.xz", "--strip-components", "1"], cwd=dirs['work_dir'])
            if retval != 0:
                self.fatal("failed to unpack gonk", exit_code=2)

            # output our sources.xml, make a copy for update_sources_xml()
            self.run_command(["cat", "sources.xml"], cwd=dirs['work_dir'])
            self.run_command(["cp", "-p", "sources.xml", "sources.xml.original"], cwd=dirs['work_dir'])

        gecko_config = self.load_gecko_config()
        extra_tarballs = self.config.get('additional_source_tarballs', [])
        if 'additional_source_tarballs' in gecko_config:
            extra_tarballs.extend(gecko_config['additional_source_tarballs'])

        for tarball in extra_tarballs:
            self.run_command(tar + ["xf", tarball], cwd=dirs['work_dir'],
                             halt_on_failure=True)

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
        l10n_git_sha = self.query_mapper_git_revision(url, 'l10n', revision, project_name="l10n %s" % locale,
                                                      require_answer=self.config.get('require_git_rev', True))
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
            # XXX Bug here. We shouldn't look for a specific comment, and
            # instead put these new nodes at the beginning / end.
            if 'Gonk specific things' in line:
                new_sources.append('  <!-- Mercurial-Information: <remote fetch="http://hg.mozilla.org/" name="hgmozillaorg"> -->')
                new_sources.append('  <!-- Mercurial-Information: <project name="%s" path="gecko" remote="hgmozillaorg" revision="%s"/> -->' %
                                   (self.buildbot_config['properties']['repo_path'], self.buildbot_properties['gecko_revision']))
                if gecko_config.get('config_version', 0) < 2 and 'gaia_revision' in self.buildbot_properties:
                    new_sources.append('  <!-- Mercurial-Information: <project name="%s" path="gaia" remote="hgmozillaorg" revision="%s"/> -->' %
                                       (gaia_config['repo'].replace('http://hg.mozilla.org/', ''), self.buildbot_properties['gaia_revision']))

                if self.query_do_translate_hg_to_git():
                    url = manifest_config['translate_base_url']
                    gecko_git = self.query_mapper_git_revision(url, 'gecko', self.buildbot_properties['gecko_revision'],
                                                               require_answer=self.config.get('require_git_rev', True))
                    new_sources.append('  <project name="%s" path="gecko" remote="mozillaorg" revision="%s"/>' % ("https://git.mozilla.org/releases/gecko.git".replace(git_base_url, ''), gecko_git))
                    # We don't need to use mapper for gaia after config version
                    # 2, since that's when we switched to pulling gaia directly
                    # from git
                    if gecko_config.get('config_version', 0) < 2:
                        if 'gaia_revision' in self.buildbot_properties:
                            gaia_git = self.query_mapper_git_revision(url, 'gaia', self.buildbot_properties['gaia_revision'],
                                                                      require_answer=self.config.get('require_git_rev', True))
                            new_sources.append('  <project name="%s" path="gaia" remote="mozillaorg" revision="%s"/>' %
                                               ("https://git.mozilla.org/releases/gaia.git".replace(git_base_url, ''), gaia_git))

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

        self.write_b2g_config()

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

        self.write_b2g_config()

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

        self.write_b2g_config()

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

        public_files = []
        public_upload_patterns = []
        public_upload_patterns = gecko_config.get('public_upload_files', [])
        # Copy gaia profile
        if gecko_config.get('package_gaia', True):
            zip_name = os.path.join(dirs['work_dir'], "gaia.zip")
            self.info("creating %s" % zip_name)
            cmd = ['zip', '-r', '-9', '-u', zip_name, 'gaia/profile']
            if self.run_command(cmd, cwd=dirs['work_dir']) != 0:
                self.fatal("problem zipping up gaia")
            self.copy_to_upload_dir(zip_name)
            if public_upload_patterns:
                public_files.append(zip_name)

        self.info("copying files to upload directory")
        files = []

        files.append(os.path.join(output_dir, 'system', 'build.prop'))

        upload_patterns = gecko_config.get('upload_files', [])
        for base_pattern in upload_patterns + public_upload_patterns:
            pattern = base_pattern.format(objdir=self.objdir, workdir=dirs['work_dir'], srcdir=dirs['src'])
            for f in glob.glob(pattern):
                if base_pattern in upload_patterns:
                    files.append(f)
                if base_pattern in public_upload_patterns:
                    public_files.append(f)

        for base_f in files + public_files:
            f = base_f
            if f.endswith(".img"):
                if self.query_is_nightly():
                    # Compress it
                    if os.path.exists(f):
                        self.info("compressing %s" % f)
                        self.run_command(["bzip2", "-f", f])
                    elif not os.path.exists("%s.bz2" % f):
                        self.error("%s doesn't exist to bzip2!" % f)
                        self.return_code = 2
                        continue
                    f = "%s.bz2" % base_f
                else:
                    # Skip it
                    self.info("not uploading %s for non-nightly build" % f)
                    continue
            if base_f in files:
                self.info("copying %s to upload directory" % f)
                self.copy_to_upload_dir(f)
            if base_f in public_files:
                self.info("copying %s to public upload directory" % f)
                self.copy_to_upload_dir(base_f, upload_dir=dirs['abs_public_upload_dir'])

        self.copy_logs_to_upload_dir()

    def _do_rsync_upload(self, upload_dir, ssh_key, ssh_user, remote_host,
                         remote_path, remote_symlink_path):
        retval = self.rsync_upload_directory(upload_dir, ssh_key, ssh_user,
                                             remote_host, remote_path)
        if retval is not None:
            self.error("Failed to upload %s to %s@%s:%s!" % (upload_dir, ssh_user, remote_host, remote_path))
            self.return_code = 2
            return -1
        upload_url = "http://%(remote_host)s/%(remote_path)s" % dict(
            remote_host=remote_host,
            remote_path=remote_path,
        )
        self.info("Upload successful: %s" % upload_url)

        if remote_symlink_path:
            ssh = self.query_exe('ssh')
            # First delete the symlink if it exists
            cmd = [ssh,
                   '-l', ssh_user,
                   '-i', ssh_key,
                   remote_host,
                   'rm -f %s' % remote_symlink_path,
                   ]
            retval = self.run_command(cmd)
            if retval != 0:
                self.error("failed to delete latest symlink")
                self.return_code = 2
            # Now create the symlink
            rel_path = os.path.relpath(remote_path, os.path.dirname(remote_symlink_path))
            cmd = [ssh,
                   '-l', ssh_user,
                   '-i', ssh_key,
                   remote_host,
                   'ln -sf %s %s' % (rel_path, remote_symlink_path),
                   ]
            retval = self.run_command(cmd)
            if retval != 0:
                self.error("failed to create latest symlink")
                self.return_code = 2

    def _do_postupload_upload(self, upload_dir, ssh_key, ssh_user, remote_host,
                              postupload_cmd):
        ssh = self.query_exe('ssh')
        remote_path = self.get_output_from_command(
            [ssh, '-l', ssh_user, '-i', ssh_key, remote_host, 'mktemp -d']
        )
        if not remote_path.endswith('/'):
            remote_path += '/'
        retval = self.rsync_upload_directory(upload_dir, ssh_key, ssh_user,
                                             remote_host, remote_path)
        if retval is not None:
            self.error("Failed to upload %s to %s@%s:%s!" % (upload_dir, ssh_user, remote_host, remote_path))
            self.return_code = 2
        else:  # post_upload.py
            upload_url = "http://%(remote_host)s/%(remote_path)s" % dict(
                remote_host=remote_host,
                remote_path=remote_path,
            )
            # build filelist
            filelist = []
            for dirpath, dirname, filenames in os.walk(upload_dir):
                for f in filenames:
                    # use / instead of os.path.join() because this is part of
                    # a post_upload.py call on a fileserver, which is probably
                    # not windows
                    path = '%s/%s' % (dirpath, f)
                    path = path.replace(upload_dir, remote_path)
                    filelist.append(path)
            cmd = [ssh,
                   '-l', ssh_user,
                   '-i', ssh_key,
                   remote_host,
                   '%s %s %s' % (postupload_cmd, remote_path, ' '.join(filelist))
                   ]
            retval = self.run_command(cmd)
            if retval != 0:
                self.error("failed to run %s!" % postupload_cmd)
                self.return_code = 2
            else:
                self.info("Upload successful: %s" % upload_url)
        # cleanup, whether we ran postupload or not
        cmd = [ssh,
               '-l', ssh_user,
               '-i', ssh_key,
               remote_host,
               'rm -f %s' % remote_path
               ]

    def upload(self):
        if not self.query_do_upload():
            self.info("Uploads disabled for this build. Skipping...")
            return

        dirs = self.query_abs_dirs()
        c = self.config
        target = self.load_gecko_config().get('upload_platform', self.config['target'])
        if c.get("target_suffix"):
            target += c["target_suffix"]
        if self.config.get('debug_build'):
            target += "-debug"
        try:
            # for Try
            user = self.buildbot_config['sourcestamp']['changes'][0]['who']
        except (KeyError, IndexError):
            user = "unknown"

        replace_dict = dict(
            branch=self.query_branch(),
            target=target,
            user=user,
            revision=self.query_revision(),
            buildid=self.query_buildid(),
        )
        upload_path_key = 'upload_remote_path'
        upload_symlink_key = 'upload_remote_symlink'
        postupload_key = 'post_upload_cmd'
        if self.query_is_nightly():
            # Dates should be based on buildid
            build_date = self.query_buildid()
            if build_date:
                try:
                    build_date = datetime.strptime(build_date, "%Y%m%d%H%M%S")
                except ValueError:
                    build_date = None
            if build_date is None:
                # Default to now
                build_date = datetime.now()
            replace_dict.update(dict(
                year=build_date.year,
                month=build_date.month,
                day=build_date.day,
                hour=build_date.hour,
                minute=build_date.minute,
                second=build_date.second,
            ))
            upload_path_key = 'upload_remote_nightly_path'
            upload_symlink_key = 'upload_remote_nightly_symlink'
            postupload_key = 'post_upload_nightly_cmd'

        # default upload
        upload_path = self.config['upload']['default'][upload_path_key] % replace_dict
        if not self._do_rsync_upload(
            dirs['abs_upload_dir'],
            self.config['upload']['default']['ssh_key'],
            self.config['upload']['default']['ssh_user'],
            self.config['upload']['default']['upload_remote_host'],
            upload_path,
            self.config['upload']['default'].get(upload_symlink_key, '') % replace_dict,
        ):  # successful; sendchange
            # TODO unhardcode
            download_url = "http://pvtbuilds.pvt.build.mozilla.org%s" % upload_path

            if self.config["target"] == "panda" and self.config.get('sendchange_masters'):
                self.sendchange(downloadables=[download_url, "%s/%s" % (download_url, "gaia-tests.zip")])
            if self.config["target"] == "generic" and self.config.get('sendchange_masters'):
                # yay hardcodes
                downloadables = [
                    '%s/%s' % (download_url, 'emulator.tar.gz'),
                ]
                matches = glob.glob(os.path.join(dirs['abs_upload_dir'], 'b2g*crashreporter-symbols.zip'))
                if matches:
                    downloadables.append("%s/%s" % (download_url, os.path.basename(matches[0])))
                matches = glob.glob(os.path.join(dirs['abs_upload_dir'], 'b2g*tests.zip'))
                if matches:
                    downloadables.append("%s/%s" % (download_url, os.path.basename(matches[0])))
                    self.sendchange(downloadables=downloadables)

        if os.path.exists(dirs['abs_public_upload_dir']) and self.config['upload'].get('public'):
            self.info("Uploading public bits...")
            self._do_postupload_upload(
                dirs['abs_public_upload_dir'],
                self.config['upload']['public']['ssh_key'],
                self.config['upload']['public']['ssh_user'],
                self.config['upload']['public']['upload_remote_host'],
                self.config['upload']['public'][postupload_key] % replace_dict,
            )

    def make_socorro_json(self):
        self.info("Creating socorro.json...")
        dirs = self.query_abs_dirs()
        socorro_dict = {
            'buildid': self.query_buildid(),
            'version': self.query_version(),
            'update_channel': self.query_update_channel(),
            #'beta_number': n/a until we build b2g beta releases
        }
        file_path = os.path.join(dirs['abs_work_dir'], 'socorro.json')
        fh = open(file_path, 'w')
        json.dump(socorro_dict, fh)
        fh.close()
        self.run_command(["cat", file_path])

    def upload_source_manifest(self):
        manifest_config = self.config.get('manifest')
        branch = self.query_branch()
        if not manifest_config or not branch:
            self.info("No manifest config or can't get branch from build. Skipping...")
            return
        if branch not in manifest_config['branches']:
            self.info("Manifest upload not enabled for this branch. Skipping...")
            return
        dirs = self.query_abs_dirs()
        upload_dir = dirs['abs_upload_dir'] + '-manifest'
        # Delete the upload dir so we don't upload previous stuff by accident
        self.rmtree(upload_dir)
        target = self.load_gecko_config().get('upload_platform', self.config['target'])
        if self.config['manifest'].get('target_suffix'):
            target += self.config['manifest']['target_suffix']
        buildid = self.query_buildid()

        if self.query_is_nightly():
            version = manifest_config['branches'][branch]
            upload_remote_basepath = self.config['manifest']['upload_remote_basepath'] % {'version': version}
            # Dates should be based on buildid
            if buildid:
                try:
                    buildid = datetime.strptime(buildid, "%Y%m%d%H%M%S")
                except ValueError:
                    buildid = None
            if buildid is None:
                # Default to now
                buildid = datetime.now()
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
            tbpl_string = None
        else:
            upload_remote_basepath = self.config['manifest']['depend_upload_remote_basepath'] % {
                'branch': branch,
                'platform': target,
                'buildid': buildid,
            }
            sha = self.query_sha512sum(os.path.join(dirs['work_dir'], 'sources.xml'))
            xmlfilename = "sources-%s.xml" % sha
            tbpl_string = "TinderboxPrint: sources.xml: http://%s%s/%s" % (
                self.config['manifest']['upload_remote_host'],
                upload_remote_basepath,
                xmlfilename,
            )
            self.copy_to_upload_dir(
                os.path.join(dirs['work_dir'], 'sources.xml'),
                os.path.join(upload_dir, 'sources.xml')
            )

        self.copy_to_upload_dir(
            os.path.join(dirs['work_dir'], 'sources.xml'),
            os.path.join(upload_dir, xmlfilename)
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
            return
        if tbpl_string:
            self.info(tbpl_string)

        if self.query_is_nightly():
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
                return
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
        update_channel = self.query_update_channel()
        publish_channel = self.config.get('publish_channel', update_channel)
        mar_url = mar_url.format(
            update_channel=update_channel,
            publish_channel=publish_channel,
            version=self.query_b2g_version(),
            target=self.config['target'],
        )

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
        update_channel = self.query_update_channel()
        publish_channel = self.config.get('publish_channel', update_channel)
        if publish_channel is None:
            publish_channel = update_channel
        upload_remote_basepath = self.config['update']['upload_remote_basepath']
        upload_remote_basepath = upload_remote_basepath.format(
            update_channel=update_channel,
            publish_channel=publish_channel,
            version=self.query_b2g_version(),
            target=self.config['target'],
        )
        retval = self.rsync_upload_directory(
            upload_dir,
            self.config['update']['ssh_key'],
            self.config['update']['ssh_user'],
            self.config['update']['upload_remote_host'],
            upload_remote_basepath,
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
                upload_remote_basepath,
            )

            if retval is not None:
                self.error("failed to upload")
                self.return_code = 2
            else:
                self.info("Upload successful")


# main {{{1
if __name__ == '__main__':
    myScript = B2GBuild()
    myScript.run_and_exit()
