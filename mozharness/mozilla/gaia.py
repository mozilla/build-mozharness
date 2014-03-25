"""
Module for performing gaia-specific tasks
"""

import os

from mozharness.base.errors import HgErrorList


class GaiaMixin(object):

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
        git = False

        print 'dest', dest

        if use_gaia_json:
            url = "{repo_path}/raw-file/{revision}/b2g/config/gaia.json".format(
                  repo_path=repo_path,
                  revision=revision)
            contents = self.retry(self.load_json_from_url, args=(url,))
            if contents.get('git') and contents['git'].get('remote'):
                git = True
                remote = contents['git']['remote']
                branch = contents['git'].get('branch')
                revision = contents['git'].get('revision')
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
                output = self.get_output_from_command(cmd, cwd=os.path.dirname(dest))
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
                             halt_on_failure=True)

            # checkout git branch
            cmd = [git_cmd,
                   'checkout',
                   revision or branch]
            self.run_command(cmd, cwd=dest, halt_on_failure=True)

            # verify
            cmd = [git_cmd]
            if revision:
                cmd += ['log', '-1']
            else:
                cmd += ['branch']
            self.run_command(cmd, cwd=dest, halt_on_failure=True)

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
