#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
""" b2g_bumper.py

    Updates a gecko repo with up to date information from B2G repositories.

    In particular, it updates gaia.json which is used by B2G desktop builds,
    and updates the XML manifests used by device builds.

    This is to tie the external repository revisions to a visible gecko commit
    which appears on TBPL, so sheriffs can blame the appropriate changes.
"""

import os
import sys
import functools
from multiprocessing.pool import ThreadPool
import subprocess
import time
from urlparse import urlparse
try:
    import simplejson as json
    assert json
except ImportError:
    import json

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import HgErrorList
from mozharness.base.vcs.vcsbase import VCSScript
from mozharness.mozilla import repo_manifest
from mozharness.base.log import ERROR


class B2GBumper(VCSScript):

    def __init__(self, require_config_file=True):
        super(B2GBumper, self).__init__(
            all_actions=[
                'clobber',
                'checkout-gecko',
                'bump-gaia',
                'checkout-manifests',
                'massage-manifests',
                'commit-manifests',
                'push',
                'push-loop',
            ],
            default_actions=[
                'push-loop',
            ],
            require_config_file=require_config_file,
        )

        # Mapping of device name to manifest
        self.device_manifests = {}

        # Cache of (remote url, refname) to revision hashes
        self._git_ref_cache = {}

        # Have we missed some gaia revisions?
        self.truncated_revisions = False

    # Helper methods {{{1
    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs

        abs_dirs = super(B2GBumper, self).query_abs_dirs()

        abs_dirs.update({
            'manifests_dir':
            os.path.join(abs_dirs['abs_work_dir'], 'manifests'),
            'gecko_local_dir':
            os.path.join(abs_dirs['abs_work_dir'],
                         self.config['gecko_local_dir']),
        })
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def query_manifest(self, device_name):
        if device_name in self.device_manifests:
            return self.device_manifests[device_name]
        dirs = self.query_abs_dirs()
        c = self.config
        manifest_file = c['devices'][device_name].get('manifest_file',
                                                      '%s.xml' % device_name)
        manifest_file = os.path.join(dirs['manifests_dir'], manifest_file)
        self.info("Loading %s" % manifest_file)
        manifest = repo_manifest.load_manifest(manifest_file)
        self.device_manifests[device_name] = manifest
        return manifest

    def filter_projects(self, device_config, manifest):
        for p in device_config['ignore_projects']:
            removed = repo_manifest.remove_project(manifest, path=p)
            if removed:
                self.info("Removed %s" % removed.toxml())

    def filter_groups(self, device_config, manifest):
        for g in device_config.get('ignore_groups', []):
            removed = repo_manifest.remove_group(manifest, g)
            for r in removed:
                self.info("Removed %s" % r.toxml())

    def map_remotes(self, manifest):
        mapping_func = functools.partial(
            repo_manifest.map_remote,
            mappings=self.config['repo_remote_mappings'])
        repo_manifest.rewrite_remotes(manifest, mapping_func)

    def resolve_git_ref(self, remote_url, revision):
        cmd = ['git', 'ls-remote', remote_url, revision]
        self.info("Running %s" % cmd)
        # Retry this a few times, in case there are network errors or somesuch
        max_retries = 5
        for _ in range(max_retries):
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            if proc.wait() != 0:
                self.warning("Returned %i - sleeping and retrying" %
                             proc.returncode)
                self.warning("Got output: %s" % proc.stdout.read())
                time.sleep(30)
                continue
            output = proc.stdout.read()
            self.info("Got output: %s" % output)
            revision = output.split()[0].strip()
            self._git_ref_cache[remote_url, revision] = revision
            return revision
        return None

    def resolve_refs(self, manifest):
        worker_pool = ThreadPool(20)
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

            # Check to see if we've looked up this revision on this remote
            # before If we have, reuse the previous value rather than looking
            # it up again This will make sure revisions for the same ref name
            # are consistent between devices, as long as they use the same
            # remote/refname
            if (remote_url, revision) in self._git_ref_cache:
                abs_revision = self._git_ref_cache[remote_url, revision]
                self.info(
                    "Re-using previous lookup %s:%s -> %s" %
                    (remote_url, revision, abs_revision))
                p.setAttribute('revision', abs_revision)
                continue

            # If there's no '/' in the revision, assume it's a head
            if '/' not in revision:
                revision = 'refs/heads/%s' % revision

            self.debug("Getting revision for %s (currently %s)" %
                       (name, revision))
            async_result = worker_pool.apply_async(self.resolve_git_ref,
                                                   (remote_url, revision))
            results.append((p, async_result))

        # TODO: alert/notify on missing repositories
        # TODO: Add external caching
        for p, result in results:
            abs_revision = result.get()
            remote_url = repo_manifest.get_project_remote_url(manifest, p)
            revision = repo_manifest.get_project_revision(manifest, p)
            if not abs_revision:
                self.fatal("Couldn't resolve %s %s" % (remote_url, revision))
            # Save to our cache
            self._git_ref_cache[remote_url, revision] = abs_revision
            p.setAttribute('revision', abs_revision)

    def cleanup_manifest(self, manifest):
        repo_manifest.cleanup(manifest)
        # Also fill out the remote for projects that are using the default
        default = repo_manifest.get_default(manifest)
        for p in manifest.getElementsByTagName('project'):
            if not p.hasAttribute('remote'):
                p.setAttribute('remote', default.getAttribute('remote'))

    def query_manifest_path(self, device):
        dirs = self.query_abs_dirs()
        device_config = self.config['devices'][device]
        manifest_file = os.path.join(
            dirs['gecko_local_dir'],
            'b2g', 'config',
            device_config.get('gecko_device_dir', device),
            'sources.xml')
        return manifest_file

    def hg_add(self, repo_path, path):
        """
        Runs 'hg add' on path
        """
        hg = self.query_exe('hg', return_type='list')
        cmd = hg + ['add', path]
        self.run_command(cmd, cwd=repo_path)

    def hg_commit(self, repo_path, message):
        """
        Commits changes in repo_path, with specified user and commit message
        """
        user = self.config['hg_user']
        hg = self.query_exe('hg', return_type='list')
        cmd = hg + ['commit', '-u', user, '-m', message]
        env = self.query_env(partial_env={'LANG': 'en_US.UTF-8'})
        status = self.run_command(cmd, cwd=repo_path, env=env)
        return status == 0

    def hg_push(self, repo_path):
        hg = self.query_exe('hg', return_type='list')
        command = hg + ["push", "-e",
                        "ssh -oIdentityFile=%s -l %s" % (
                            self.config["ssh_key"], self.config["ssh_user"],
                        ),
                        self.config["gecko_push_url"]]
        status = self.run_command(command, cwd=repo_path,
                                  error_list=HgErrorList)
        if status != 0:
            # We failed; get back to a known state so we can either retry
            # or fail out and continue later.
            self.run_command(hg + ["--config", "extensions.mq=",
                                   "strip", "--no-backup", "outgoing()"],
                             cwd=repo_path)
            self.run_command(hg + ["up", "-C"],
                             cwd=repo_path)
            self.run_command(hg + ["--config", "extensions.purge=",
                                   "purge", "--all"],
                             cwd=repo_path)
            return False
        return True

    def _read_json(self, path):
        if not os.path.exists(path):
            self.error("%s doesn't exist!" % path)
            return
        contents = self.read_from_file(path)
        try:
            json_contents = json.loads(contents)
            return json_contents
        except ValueError:
            self.error("%s is invalid json!" % path)

    def get_revision_list(self, repo_config, prev_revision=None):
        revision_list = []
        url = repo_config['polling_url']
        branch = repo_config.get('branch', 'default')
        max_revisions = self.config['gaia_max_revisions']
        dirs = self.query_abs_dirs()
        if prev_revision:
            # hgweb json-pushes hardcode
            url += '&fromchange=%s' % prev_revision
        file_name = os.path.join(dirs['abs_work_dir'],
                                 '%s.json' % repo_config['repo_name'])
        # might be nice to have a load-from-url option; til then,
        # download then read
        if self.retry(
            self.download_file,
            args=(url, ),
            kwargs={'file_name': file_name},
            error_level=ERROR,
            sleeptime=0,
        ) != file_name:
            return None
        contents = self.read_from_file(file_name)
        revision_dict = json.loads(contents)
        if not revision_dict:
            return []
        # Discard any revisions not on the branch we care about.
        for k in sorted(revision_dict, key=int):  # numeric sort
            v = revision_dict[k]
            if v['changesets'][-1]['branch'] == branch:
                revision_list.append(v)
        # Limit the list to max_revisions.
        # Set a flag, so we can update the commit message with a warning
        # that we've truncated the list.
        if len(revision_list) > max_revisions:
            self.truncated_revisions = True
        return revision_list[-max_revisions:]

    def update_gaia_json(self, path, revision, repo_path):
        """ Update path with repo_path + revision.

            If the revision hasn't changed, don't do anything.
            If the repo_path changes or the current json is invalid, error but don't fail.
            """
        if not os.path.exists(path):
            self.add_summary(
                "%s doesn't exist; can't update with repo_path %s revision %s!" % (path, repo_path, revision),
                level=ERROR,
            )
            return -1
        contents = self._read_json(path)
        if contents:
            if contents.get("repo_path") != repo_path:
                self.error("Current repo_path %s differs from %s!" % (str(contents.get("repo_path")), repo_path))
            if contents.get("revision") == revision:
                self.info("Revision %s is the same.  No action needed." % revision)
                self.add_summary("Revision %s is unchanged for repo_path %s." % (revision, repo_path))
                return 0
        contents = {
            "repo_path": repo_path,
            "revision": revision
        }
        if self.write_to_file(path, json.dumps(contents, indent=4) + "\n") != path:
            self.add_summary(
                "Unable to update %s with new revision %s!" % (path, revision),
                level=ERROR,
            )
            return -2

    def build_commit_message(self, revision_list, repo_name, repo_url):
        revisions = []
        comments = ''
        for revision_config in reversed(revision_list):
            for changeset_config in reversed(revision_config['changesets']):
                revisions.append(changeset_config['node'])
                comments += "\n========\n"
                comments += u'\n%s/rev/%s\nAuthor: %s\nDesc: %s\n' % (
                    repo_url,
                    changeset_config['node'][:12],
                    changeset_config['author'],
                    changeset_config['desc'],
                )
        message = 'Bumping gaia.json for %d %s revision(s) a=gaia-bump\n' % (
            len(revisions),
            repo_name
        )
        if self.truncated_revisions:
            message += "Truncated some number of revisions since the previous bump.\n"
            self.truncated_revisions = False
        message += comments
        message = message.encode("utf-8")
        return message

    # Actions {{{1
    def checkout_gecko(self):
        c = self.config
        dirs = self.query_abs_dirs()
        dest = dirs['gecko_local_dir']
        repos = [{
            'repo': c['gecko_pull_url'],
            'tag': c.get('gecko_tag', 'default'),
            'dest': dest,
            'vcs': 'hgtool',
            'hgtool_base_bundle_urls': c.get('hgtool_base_bundle_urls'),
        }]
        self.vcs_checkout_repos(repos)

    def checkout_manifests(self):
        c = self.config
        dirs = self.query_abs_dirs()
        repos = [
            {'vcs': 'gittool',
             'repo': c['manifests_repo'],
             'revision': c['manifests_revision'],
             'dest': dirs['manifests_dir']},
        ]
        self.vcs_checkout_repos(repos)

    def massage_manifests(self):
        """
        For each device in config['devices'], we'll strip projects mentioned in
        'ignore_projects', or that have group attribute mentioned in
        'filter_groups'.
        We'll also map remote urls
        Finally, we'll resolve absolute refs for projects that aren't fully
        specified.
        """
        for device, device_config in self.config['devices'].items():
            self.info("Massaging manifests for %s" % device)
            manifest = self.query_manifest(device)
            self.filter_projects(device_config, manifest)
            self.filter_groups(device_config, manifest)
            self.map_remotes(manifest)
            self.resolve_refs(manifest)
            repo_manifest.cleanup(manifest)
            self.device_manifests[device] = manifest

            manifest_path = self.query_manifest_path(device)
            self.write_to_file(manifest_path, manifest.toxml())

    def commit_manifests(self):
        dirs = self.query_abs_dirs()
        repo_path = dirs['gecko_local_dir']
        for device, device_config in self.config['devices'].items():
            manifest_path = self.query_manifest_path(device)
            self.hg_add(repo_path, manifest_path)

        message = "Bumping manifests"
        return self.hg_commit(repo_path, message)

    def bump_gaia(self):
        dirs = self.query_abs_dirs()
        repo_path = dirs['gecko_local_dir']
        gaia_json_path = os.path.join(repo_path,
                                      self.config['gaia_revision_file'])
        contents = self._read_json(gaia_json_path)

        # Get the list of changes
        if contents:
            prev_revision = contents.get('revision')
        else:
            prev_revision = None

        polling_url = "%s/json-pushes?full=1" % self.config['gaia_repo_url']
        repo_config = {
            'polling_url': polling_url,
            'branch': self.config.get('gaia_branch', 'default'),
            'repo_name': 'gaia',
        }
        revision_list = self.get_revision_list(repo_config=repo_config,
                                               prev_revision=prev_revision)
        if not revision_list:
            # No changes
            return False

        # Update the gaia.json with the list of changes
        gaia_repo_path = urlparse(self.config['gaia_repo_url']).path
        revision = revision_list[-1]['changesets'][-1]['node']
        self.update_gaia_json(gaia_json_path, revision, gaia_repo_path)

        # Commit
        message = self.build_commit_message(revision_list, 'gaia',
                                            self.config['gaia_repo_url'])
        self.hg_commit(repo_path, message)
        return True

    def push(self):
        dirs = self.query_abs_dirs()
        repo_path = dirs['gecko_local_dir']
        return self.hg_push(repo_path)

    def push_loop(self):
        max_retries = 5
        for _ in range(max_retries):
            changed = False
            self.checkout_gecko()
            # TODO: Enforce b2g manifests have equivalent revision of gaia that
            # gaia.json has?
            if self.bump_gaia():
                changed = True
            self.checkout_manifests()
            self.massage_manifests()
            if self.commit_manifests():
                changed = True

            if not changed:
                # Nothing changed, we're all done
                self.info("No changes - all done")
                break

            if self.push():
                # We did it! Hurray!
                self.info("Great success!")
                break
            # If we're here, then the push failed. It also stripped any
            # outgoing commits, so we should be in a pristine state again

            # Sleep before trying again
            self.info("Sleeping 60 before trying again")
            time.sleep(60)
        else:
            self.fatal("Didn't complete successfully (hit max_retries)")

# __main__ {{{1
if __name__ == '__main__':
    bumper = B2GBumper()
    bumper.run_and_exit()
