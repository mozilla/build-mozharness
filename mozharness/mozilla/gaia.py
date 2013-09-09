"""
Module for performing gaia-specific tasks
"""

import os

from mozharness.base.errors import TarErrorList, ZipErrorList, HgErrorList


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

        print 'dest', dest

        if use_gaia_json:
            url = "{repo_path}/raw-file/{revision}/b2g/config/gaia.json".format(
                  repo_path=repo_path,
                  revision=revision)
            contents = self.retry(self.load_json_from_url, args=(url,))
            if contents.get('repo_path') and contents.get('revision'):
                repo_path = 'https://hg.mozilla.org/%s' % contents['repo_path']
                revision = contents['revision']
                branch = None

        # purge the repo if it already exists
        if os.access(dest, os.F_OK):
            cmd = [self.query_exe('hg'),
                   '--config',
                   'extensions.purge=',
                   'purge']
            if self.run_command(cmd, cwd=dest, error_list=HgErrorList):
                self.fatal("Unable to purge %s!" % repo_dir)

        repo = {
            'repo': repo_path,
            'revision': revision,
            'branch': branch,
            'dest': dest,
        }

        self.vcs_checkout_repos([repo], parent_dir=os.path.dirname(dest))

    def make_gaia(self, gaia_dir, xre_dir, debug=False):
        make = self.query_exe('make', return_type="list")
        self.run_command(make,
                         cwd=gaia_dir,
                         env={'DEBUG': '1' if debug else '0',
                              'NOFTU': '1',
                              'DESKTOP': '0',
                              'USE_LOCAL_XULRUNNER_SDK': '1',
                              'XULRUNNER_DIRECTORY': xre_dir
                              },
                         halt_on_failure=True)
