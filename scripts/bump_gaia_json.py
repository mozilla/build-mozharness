#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
""" bump_gaia_json.py

    Polls [a] gaia hg repo(s), and updates a gecko repo with the
    revision information and pushes.

    This is to tie the gaia revision to a visible TBPL gecko revision,
    so sheriffs can blame the appropriate changes.
"""

import os
import sys
import urlparse
try:
    import simplejson as json
    assert json
except ImportError:
    import json

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import HgErrorList
from mozharness.base.log import ERROR
from mozharness.base.vcs.vcsbase import MercurialScript


# BumpGaiaJson {{{1
class BumpGaiaJson(MercurialScript):
    truncated_revisions = False
    config_options = [
        [['--max-revisions', ], {
            "action": "store",
            "dest": "max_revisions",
            "type": "int",
            "default": 5,
            "help": "Limit the number of revisions to populate to this number.",
        }],
    ]

    def __init__(self, require_config_file=False):
        super(BumpGaiaJson, self).__init__(
            config_options=self.config_options,
            all_actions=[
                'clobber',
                'push-loop',
                'summary',
                # TODO
                #'notify',
            ],
            default_actions=[
                'push-loop',
                'summary',
            ],
            require_config_file=require_config_file,
        )

    # Helper methods {{{1
    def get_revision_list(self, repo_config, prev_revision=None):
        revision_list = []
        url = repo_config['polling_url']
        branch = repo_config.get('branch', 'default')
        max_revisions = self.config['max_revisions']
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

    def build_commit_message(self, revision_config, repo_name, repo_url):
        revision_list = []
        comments = ''
        for changeset_config in reversed(revision_config['changesets']):
            revision_list.append(changeset_config['node'])
            comments += "\n========\n"
            comments += u'\n%s/rev/%s\nAuthor: %s\nDesc: %s\n' % (
                repo_url,
                changeset_config['node'][:12],
                changeset_config['author'],
                changeset_config['desc'],
            )
        message = 'Bumping gaia.json for %d %s revision(s)\n' % (
            len(revision_list),
            repo_name
        )
        if self.truncated_revisions:
            message += "Truncated some number of revisions since the previous bump.\n"
            self.truncated_revisions = False
        message += comments
        message = message.encode("utf-8")
        return message

    def query_repo_path(self, repo_config):
        dirs = self.query_abs_dirs()
        return os.path.join(
            dirs['abs_work_dir'],
            repo_config['repo_name'],
            repo_config['target_repo_name'],
        )

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

    def _update_json(self, path, revision, repo_path):
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

    def _pull_target_repo(self, orig_repo_config):
        repo_config = {}
        repo_config["repo"] = orig_repo_config["target_pull_url"]
        repo_config["tag"] = orig_repo_config.get("target_tag", "default")
        repo_path = self.query_repo_path(orig_repo_config)
        repo_config["dest"] = repo_path
        repos = [repo_config]
        super(BumpGaiaJson, self).pull(repos=repos)

    def query_revision(self, revision_config):
        return revision_config['changesets'][-1]['node']

    def _do_looped_push(self, repo_config, revision_config):
        hg = self.query_exe("hg", return_type="list")
        self._pull_target_repo(repo_config)
        repo_path = self.query_repo_path(repo_config)
        gaia_config_file = os.path.join(repo_path, self.config['revision_file'])
        revision = self.query_revision(revision_config)
        parts = urlparse.urlparse(repo_config["repo_url"])
        json_repo_path = parts.path
        status = self._update_json(gaia_config_file, revision, json_repo_path)
        if status is not None:
            return status
        env = self.query_env(partial_env={'LANG': 'en_US.UTF-8'})
        message = self.build_commit_message(
            revision_config, repo_config["repo_name"],
            repo_config["repo_url"],
        )
        command = hg + ["commit", "-u", self.config['hg_user'],
                        "-m", message]
        self.run_command(command, cwd=repo_path, env=env)
        command = hg + ["push", "-e",
                        "ssh -oIdentityFile=%s -l %s" % (
                            self.config["ssh_key"], self.config["ssh_user"],
                        ),
                        repo_config["target_push_url"]]
        status = self.run_command(command, cwd=repo_path,
                                  error_list=HgErrorList)
        if status:
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
            return -1
        return 0

    # Actions {{{1
    def push_loop(self):
        """ A bit of a misnomer since we pull and update and commit as well?
            """
        for repo_config in self.config['repo_list']:
            self._pull_target_repo(repo_config)
            repo_path = self.query_repo_path(repo_config)
            contents = self._read_json(os.path.join(repo_path, self.config['revision_file']))
            prev_revision = None
            if contents:
                prev_revision = contents.get('revision')
            revision_list = self.get_revision_list(repo_config, prev_revision=prev_revision)
            if revision_list is None:
                self.add_summary(
                    "Unable to get revision_list for %s" % repo_config['repo_url'],
                    level=ERROR,
                )
                continue
            if not revision_list:
                self.add_summary("No new changes for %s" % repo_config['repo_url'])
                continue
            for revision_config in revision_list:
                if self.retry(
                    self._do_looped_push,
                    args=(repo_config, revision_config),
                ):
                    # Keep going, in case there's a further revision that has
                    # CLOSED TREE (bug 885051)
                    self.truncated_revisions = True
                    revision = self.query_revision(revision_config)
                    self.add_summary(
                        "Unable to update %s for revision %s." % (repo_config['target_push_url'], revision),
                        level=ERROR,
                    )


# __main__ {{{1
if __name__ == '__main__':
    bump_gaia_json = BumpGaiaJson()
    bump_gaia_json.run()
