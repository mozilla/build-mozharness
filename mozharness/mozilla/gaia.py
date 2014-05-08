"""
Module for performing gaia-specific tasks
"""

import os

from mozharness.base.errors import HgErrorList, BaseErrorList
from mozharness.base.log import ERROR


class GaiaMixin(object):

    npm_error_list = BaseErrorList + [
        {'substr': r'''npm ERR! Error:''', 'level': ERROR}
    ]

    # This requires self to inherit a VCSMixin.
    def clone_gaia(self, dest, repo, use_gaia_json=False):
        """
        Clones an hg mirror of gaia.

        repo: a dict containing 'repo_path', 'revision', and optionally
              'branch' parameters
        use_gaia_json: if True, the repo parameter is used to retrieve
              a gaia.json file from a gecko repo, which in turn is used to
              clone gaia; if False, repo represents a gaia repo to clone.
        """

        repo_path = repo.get('repo_path')
        revision = repo.get('revision')
        branch = repo.get('branch')
        gaia_json_path = self.config.get("gaia_json_path", "{repo_path}/raw-file/{revision}/b2g/config/gaia.json")
        git = False
        pr_num = None

        self.info('dest: %s' % dest)

        if use_gaia_json:
            url = gaia_json_path.format(
                repo_path=repo_path,
                revision=revision)
            contents = self.retry(self.load_json_from_url, args=(url,))
            if contents.get('git') and contents['git'].get('remote'):
                git = True
                remote = contents['git']['remote']
                branch = contents['git'].get('branch')
                revision = contents['git'].get('git_revision')
                pr_num = contents['git'].get('github_pr_number')
                if not (branch or revision):
                    self.fatal('Must specify branch or revision for git repo')
            elif contents.get('repo_path') and contents.get('revision'):
                repo_path = 'https://hg.mozilla.org/%s' % contents['repo_path']
                revision = contents['revision']
                branch = None

        if git:
            git_cmd = self.query_exe('git')
            needs_clobber = True

            if os.path.exists(dest) and os.path.exists(os.path.join(dest, '.git')):
                cmd = [git_cmd, 'remote', '-v']
                output = self.get_output_from_command(cmd, cwd=dest)
                for line in output:
                    if remote in line:
                        needs_clobber = False

            if needs_clobber:
                self.rmtree(dest)

            # git clone
            cmd = [git_cmd,
                   'clone',
                   remote]
            self.run_command(cmd,
                             cwd=os.path.dirname(dest),
                             output_timeout=1760,
                             halt_on_failure=True,
                             fatal_exit_code=3)

            if pr_num:
                local_pr_branch = 'local_pr_%d' % pr_num
                cmd = [git_cmd,
                       'fetch',
                       'origin',
                       '+refs/pull/%d/merge:%s' % (pr_num, local_pr_branch)]
                self.run_command(cmd,
                                 cwd=dest,
                                 output_timeout=1760,
                                 halt_on_failure=True,
                                 fatal_exit_code=3)
                # Ideally, we'd just use the merge_sha from the github api
                # but the PR object that gets sent with the hook call is
                # either an empty string for new PRs or an outdated value
                # for synchronise events.  I guess Github doesn't generate
                # a new merge sha before sending the webhook
                branch = revision = local_pr_branch

            # checkout git branch
            cmd = [git_cmd,
                   'checkout',
                   revision or branch]
            self.run_command(cmd, cwd=dest, halt_on_failure=True,
                             fatal_exit_code=3)

            # verify
            cmd = [git_cmd]
            if revision:
                cmd += ['log', '-1']
            else:
                cmd += ['branch']
            self.run_command(cmd, cwd=dest, halt_on_failure=True,
                             fatal_exit_code=3)

        else:
            # purge the repo if it already exists
            if os.path.exists(dest):
                if os.path.exists(os.path.join(dest, '.hg')):
                    # this is an hg dir, so do an hg clone
                    cmd = [self.query_exe('hg'),
                           '--config',
                           'extensions.purge=',
                           'purge']
                    if self.run_command(cmd, cwd=dest, error_list=HgErrorList):
                        self.fatal("Unable to purge %s!" % dest)
                else:
                    # there's something here, but it isn't hg; just delete it
                    self.rmtree(dest)

            repo = {
                'repo': repo_path,
                'revision': revision,
                'branch': branch,
                'dest': dest,
            }

            self.vcs_checkout_repos([repo], parent_dir=os.path.dirname(dest))

    def make_gaia(self, gaia_dir, xre_dir, debug=False, noftu=True):
        make = self.query_exe('make', return_type="list")
        self.run_command(make,
                         cwd=gaia_dir,
                         env={'DEBUG': '1' if debug else '0',
                              'NOFTU': '1' if noftu else '0',
                              'DESKTOP': '0',
                              'DESKTOP_SHIMS': '1',
                              'USE_LOCAL_XULRUNNER_SDK': '1',
                              'XULRUNNER_DIRECTORY': xre_dir
                              },
                         halt_on_failure=True)

    def make_node_modules(self):
        dirs = self.query_abs_dirs()

        self.run_command(['npm', 'cache', 'clean'])

        # run 'make node_modules' first, so we can separately handle
        # errors that occur here
        cmd = ['make',
               'node_modules',
               'NODE_MODULES_GIT_URL=https://git.mozilla.org/b2g/gaia-node-modules.git']
        kwargs = {
            'cwd': dirs['abs_gaia_dir'],
            'output_timeout': 300,
            'error_list': self.npm_error_list
        }
        code = self.retry(self.run_command, attempts=3, good_statuses=(0,),
                          args=[cmd], kwargs=kwargs)
        if code:
            # Dump npm-debug.log, if it exists
            npm_debug = os.path.join(dirs['abs_gaia_dir'], 'npm-debug.log')
            if os.access(npm_debug, os.F_OK):
                self.info('dumping npm-debug.log')
                self.run_command(['cat', npm_debug])
            else:
                self.info('npm-debug.log doesn\'t exist, not dumping')
            self.fatal('Errors during \'npm install\'', exit_code=code)
