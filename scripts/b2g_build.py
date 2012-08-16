#!/usr/bin/env python
# Mozilla licence shtuff

import sys
import os
import glob
import re

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

# import the guts
from mozharness.base.script import BaseScript
from mozharness.base.vcs.vcsbase import VCSMixin
from mozharness.base.transfer import TransferMixin
from mozharness.base.errors import MakefileErrorList
from mozharness.mozilla.mock import MockMixin
from mozharness.mozilla.tooltool import TooltoolMixin
from mozharness.mozilla.buildbot import BuildbotMixin

try:
    import simplejson as json
    assert json
except ImportError:
    import json


class B2GBuild(MockMixin, BaseScript, VCSMixin, TooltoolMixin, TransferMixin, BuildbotMixin):
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
        [["--gecko-config"], {
            "dest": "gecko_config",
            "help": "specfiy alternate location for gecko config",
        }],
        [["--disable-ccache"], {
            "dest": "ccache",
            "action": "store_false",
            "help": "disable ccache",
        }],
    ]

    def __init__(self, require_config_file=False):
        BaseScript.__init__(self,
                            config_options=self.config_options,
                            all_actions=[
                                'clobber',  # From BaseScript
                                'checkout-gecko',
                                # Download via tooltool repo in gecko checkout or via explicit url
                                'download-gonk',
                                'unpack-gonk',
                                'build',
                                'prep-upload',
                                'upload',
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
                                'repo': 'http://hg.mozilla.org/mozilla-central',  # from buildprops
                                'branch': 'mozilla-central',                      # from buildprops
                                'default_vcs': 'hg',
                                'vcs_share_base': os.environ.get('HG_SHARE_BASE_DIR'),
                                'ccache': True,
                                'buildbot_json_path': os.environ.get('PROPERTIES_FILE'),
                                'tooltool_servers': None,
                                'ssh_key': None,
                                'ssh_user': None,
                                'upload_remote_host': None,
                                'upload_remote_basepath': None,
                            },
                            )

        self.gecko_config = None

    def _pre_config_lock(self, rw_config):
        super(B2GBuild, self)._pre_config_lock(rw_config)

        if self.buildbot_config is None:
            self.info("Reading buildbot build properties...")
            self.read_buildbot_config()

        if 'target' not in self.config:
            self.fatal("Must specify --target!")

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(B2GBuild, self).query_abs_dirs()

        c = self.config
        dirs = {
            'src': os.path.join(c['work_dir'], 'gecko'),
            'work_dir': os.path.abspath(c['work_dir']),
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
            conf_file = os.path.join(dirs['src'], 'b2g', 'config', self.config['target'], 'config.json')
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
        dirs = self.query_abs_dirs()
        platform_ini = os.path.join(dirs['work_dir'], 'out', 'target',
                                    'product', self.config['target'], 'system',
                                    'b2g', 'platform.ini')
        data = open(platform_ini).read()
        buildid = re.search("^BuildID=(\d+)$", data, re.M)
        if buildid:
            return buildid.group(1)

    # Actions {{{2
    def checkout_gecko(self):
        dirs = self.query_abs_dirs()

        repo = self.query_repo()
        if self.buildbot_config and 'sourcestamp' in self.buildbot_config:
            rev = self.vcs_checkout(repo=repo, dest=dirs['src'], revision=self.buildbot_config['sourcestamp']['revision'])
        else:
            rev = self.vcs_checkout(repo=repo, dest=dirs['src'])

        self.set_buildbot_property('revision', rev, write_to_file=True)

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
                config_dir = os.path.join(dirs['src'], 'b2g', 'config', self.config['target'])
                manifest = os.path.abspath(os.path.join(config_dir, gecko_config['tooltool_manifest']))
                self.tooltool_fetch(manifest, dirs['work_dir'])
                return
            gonk_url = gecko_config['gonk_snapshot_url']

        if gonk_url:
            self.download_file(gonk_url, os.path.join(dirs['work_dir'], 'gonk.tar.xz'))

    def unpack_gonk(self):
        dirs = self.query_abs_dirs()
        self.run_command(["tar", "xf", "gonk.tar.xz", "--strip-components", "1"], cwd=dirs['work_dir'])

        # output our sources.xml
        self.run_command(["cat", "sources.xml"], cwd=dirs['work_dir'])

    def build(self):
        dirs = self.query_abs_dirs()
        gecko_config = self.load_gecko_config()
        cmd = ['./build.sh']
        env = self.query_env()
        env.update(gecko_config.get('env', {}))
        if self.config['ccache']:
            env['CCACHE_BASEDIR'] = dirs['work_dir']

        # TODO: make sure we pass MOZ_BUILD_DATE

        # Write .userconfig to point to the correct object directory for gecko
        # Normally this is embedded inside the .config file included with the snapshot
        user_config = open(os.path.join(dirs['work_dir'], '.userconfig'), 'w')
        user_config.write("GECKO_OBJDIR=%s/objdir-gecko\n" % dirs['work_dir'])
        user_config.close()

        if 'mock_target' in gecko_config:
            # initialize mock
            self.setup_mock(gecko_config['mock_target'], gecko_config['mock_packages'])
            if self.config['ccache']:
                self.run_mock_command(gecko_config['mock_target'], 'ccache -z', cwd=dirs['work_dir'], env=env)

            retval = self.run_mock_command(gecko_config['mock_target'], cmd, cwd=dirs['work_dir'], env=env, error_list=MakefileErrorList)
            if self.config['ccache']:
                self.run_mock_command(gecko_config['mock_target'], 'ccache -s', cwd=dirs['work_dir'], env=env)
        else:
            if self.config['ccache']:
                self.run_command('ccache -z', cwd=dirs['work_dir'], env=env)
            retval = self.run_command(cmd, cwd=dirs['work_dir'], env=env, error_list=MakefileErrorList)
            if self.config['ccache']:
                self.run_command('ccache -s', cwd=dirs['work_dir'], env=env)

        if retval != 0:
            self.fatal("failed to build", exit_code=2)

    def prep_upload(self):
        # Copy stuff into build/upload directory
        dirs = self.query_abs_dirs()

        output_dir = os.path.join(dirs['work_dir'], 'out', 'target', 'product', self.config['target'])
        self.info("copying files to upload directory")
        files = []
        files.append(os.path.join(output_dir, 'system', 'build.prop'))
        files.append(os.path.join(dirs['work_dir'], 'sources.xml'))
        for f in files:
            self.info("copying %s to upload directory" % f)
            self.copy_to_upload_dir(f)

        for f in glob.glob("%s/*.img" % output_dir):
            self.info("copying %s to upload directory" % f)
            self.copy_to_upload_dir(f)
            f = os.path.join(dirs['abs_upload_dir'], os.path.basename(f))
            self.info("compressing %s" % f)
            self.run_command(['gzip', '-f', f])

        self.copy_logs_to_upload_dir()

    def upload(self):
        dirs = self.query_abs_dirs()
        upload_path = "%(basepath)s/%(branch)s-%(target)s/%(buildid)s" % dict(
            basepath=self.config['upload_remote_basepath'],
            branch=self.query_branch(),
            buildid=self.query_buildid(),
            target=self.config['target'],
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

            self.info("Upload successful: %s" % upload_url)

# main {{{1
if __name__ == '__main__':
    myScript = B2GBuild()
    myScript.run()
