#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
""" b2g_make_manifest.py

Create fully resolved XML manifests for B2G builds by following <include>
directives, resolving reference names into commit ids, mapping remotes, and
removing groups
"""
import os
import sys
import functools
from multiprocessing.pool import ThreadPool
import subprocess

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.vcs.vcsbase import VCSScript

from mozharness.mozilla import repo_manifest


class MakeManifestScript(VCSScript):
    config_options = [
        [['--revision'], {
            'action': 'store',
            'dest': 'revision',
            'help': 'branch or revision of manifests to use',
            'default': 'master',
        }],
        [['--manifest-repo'], {
            'action': 'store',
            'dest': 'manifest_repo',
            'help': 'repository where original manifests are located',
            'default': 'https://git.mozilla.org/b2g/b2g-manifest.git',
        }],
        [['--ignore-group'], {
            'action': 'append',
            'dest': 'ignore_groups',
            'help': 'project groups to ignore',
            'default': [],
        }],
        [['--ignore-project'], {
            'action': 'append',
            'dest': 'ignore_projects',
            'help': 'projects to ignore (by path)',
            'default': [],
        }],
        [['--manifest-name'], {
            'action': 'store',
            'dest': 'manifest_name',
            'help': 'which manifest to process from the manifest repo',
            'default': None,
        }],
        [['--manifest-file'], {
            'action': 'store',
            'dest': 'manifest_file',
            'help': 'which manifest file to process. overrides manifest_name',
            'default': None,
        }],
        [['--output'], {
            'action': 'store',
            'dest': 'output',
            'help': 'where to store the output',
            'default': None,
        }],
    ]

    all_actions = [
        'clobber',
        'checkout-manifests',
        'filter-projects',
        'filter-groups',
        'map-remotes',
        'resolve-refs',
        'write-manifest',
    ]

    default_actions = all_actions

    def __init__(self):
        super(MakeManifestScript, self).__init__(
            config_options=self.config_options,
            all_actions=self.all_actions,
            default_actions=self.default_actions,
            config={
                'repo_remote_mappings': {
                    'https://android.googlesource.com/': 'https://git.mozilla.org/external/aosp',
                    'git://codeaurora.org/': 'https://git.mozilla.org/external/caf',
                    'git://github.com/mozilla-b2g/': 'https://git.mozilla.org/b2g',
                    'git://github.com/mozilla/': 'https://git.mozilla.org/b2g',
                    'https://git.mozilla.org/releases': 'https://git.mozilla.org/releases',
                    'http://android.git.linaro.org/git-ro/': 'https://git.mozilla.org/external/linaro',
                    'git://github.com/apitrace/': 'https://git.mozilla.org/external/apitrace',
                    # Some mappings to ourself, we want to leave these as-is!
                    'https://git.mozilla.org/external/aosp': 'https://git.mozilla.org/external/aosp',
                    'https://git.mozilla.org/external/caf': 'https://git.mozilla.org/external/caf',
                    'https://git.mozilla.org/b2g': 'https://git.mozilla.org/b2g',
                    'https://git.mozilla.org/external/apitrace': 'https://git.mozilla.org/external/apitrace',
            }}
        )
        self.manifest = None

    def _pre_config_lock(self, rw_config):
        super(MakeManifestScript, self)._pre_config_lock(rw_config)

        if not ('manifest_name' in self.config or 'manifest_file' in self.config):
            self.fatal("Must specify --manifest-name or --manifest-file!")
        if 'output' not in self.config:
            self.fatal("Must specify --output!")

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs

        abs_dirs = super(MakeManifestScript, self).query_abs_dirs()

        abs_dirs.update({
            'manifests_dir':
            os.path.join(abs_dirs['abs_work_dir'], 'manifests'),
        })
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def query_manifest(self):
        if self.manifest:
            return self.manifest
        dirs = self.query_abs_dirs()
        c = self.config
        manifest_file = c.get('manifest_file')
        if not manifest_file:
            manifest_file = os.path.join(dirs['manifests_dir'],
                                        c['manifest_name'] + ".xml")
        self.info("Loading %s" % manifest_file)
        self.manifest = repo_manifest.load_manifest(manifest_file)
        return self.manifest

    def checkout_manifests(self):
        c = self.config
        if 'manifest_file' in c:
            self.info("Skipping checkout_manifests since we're using a local manifest file")
            return
        dirs = self.query_abs_dirs()
        repos = [
            {'vcs': 'gittool',
             'repo': c['manifest_repo'],
             'revision': c['revision'],
             'dest': dirs['manifests_dir']},
        ]
        self.vcs_checkout_repos(repos)

    def filter_projects(self):
        manifest = self.query_manifest()
        for p in self.config['ignore_projects']:
            removed = repo_manifest.remove_project(manifest, path=p)
            if removed:
                self.info("Removed %s" % removed.toxml())

    def filter_groups(self):
        manifest = self.query_manifest()
        for g in self.config['ignore_groups']:
            removed = repo_manifest.remove_group(manifest, g)
            for r in removed:
                self.info("Removed %s" % r.toxml())

    def map_remotes(self):
        manifest = self.query_manifest()
        mapping_func = functools.partial(
            repo_manifest.map_remote,
            mappings=self.config['repo_remote_mappings'])
        repo_manifest.rewrite_remotes(manifest, mapping_func)

    def resolve_git_ref(self, remote_url, revision):
        cmd = ['git', 'ls-remote', remote_url, revision]
        self.info("Running %s" % cmd)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        proc.wait()
        output = proc.stdout.read()
        self.info("Got output %s" % output)
        revision = output.split()[0].strip()
        return revision

    def resolve_refs(self):
        manifest = self.query_manifest()

        worker_pool = ThreadPool(8)
        results = []

        # Resolve refnames
        for p in manifest.getElementsByTagName('project'):
            name = p.getAttribute('name')
            remote_url = repo_manifest.get_project_remote_url(manifest, p)
            revision = repo_manifest.get_project_revision(manifest, p)
            # commit ids are already done
            if repo_manifest.is_commitid(revision):
                self.debug("%s is already locked to %s; skipping" %
                           (name, revision))
                continue

            # If there's no '/' in the revision, assume it's a head
            if '/' not in revision:
                revision = 'refs/heads/%s' % revision

            self.debug("Getting revision for %s (currently %s)" %
                       (name, revision))
            async_result = worker_pool.apply_async(self.resolve_git_ref, (remote_url, revision))
            results.append((p, async_result))

        for p, result in results:
            revision = result.get()
            p.setAttribute('revision', revision)

    def write_manifest(self):
        manifest = self.query_manifest()
        default = repo_manifest.get_default(manifest)
        for p in manifest.getElementsByTagName('project'):
            if not p.hasAttribute('remote'):
                p.setAttribute('remote', default.getAttribute('remote'))
        repo_manifest.cleanup(manifest)
        c = self.config
        self.write_to_file(c['output'], manifest.toxml())


if __name__ == '__main__':
    script = MakeManifestScript()
    script.run_and_exit()
