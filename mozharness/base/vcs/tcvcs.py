import os.path
from mozharness.base.script import ScriptMixin
from mozharness.base.log import LogMixin, OutputParser
from mozharness.base.errors import VCSException

class TcVCS(ScriptMixin, LogMixin):
    def __init__(self, log_obj=None, config=None, vcs_config=None,
                 script_obj=None):
        super(TcVCS, self).__init__()

        self.log_obj = log_obj
        self.script_obj = script_obj
        if config:
            self.config = config
        else:
            self.config = {}
        # vcs_config = {
        #  repo: repository,
        #  branch: branch,
        #  revision: revision,
        #  ssh_username: ssh_username,
        #  ssh_key: ssh_key,
        # }
        self.vcs_config = vcs_config
        self.tc_vcs = self.query_exe('tc-vcs', return_type='list')

    def ensure_repo_and_revision(self):
        """Makes sure that `dest` is has `revision` or `branch` checked out
        from `repo`.

        Do what it takes to make that happen, including possibly clobbering
        dest.
        """
        c = self.vcs_config
        for conf_item in ('dest', 'repo'):
            assert self.vcs_config[conf_item]
        dest = os.path.abspath(c['dest'])
        repo = c['repo']
        branch = c.get('branch')
        revision = c.get('revision')

        if not os.path.exists(dest):
            base_repo = self.config.get('base_repo', repo)
            cmd = self.tc_vcs[:]
            cmd.extend(['clone', base_repo, dest])
            if self.run_command(cmd):
                raise VCSException("Unable to checkout")

        if not branch:
            branch = "master"

        if revision:
            cmd = self.tc_vcs[:]
            cmd.extend(['checkout-revision', dest, repo, branch, revision])
            if self.run_command(cmd):
                raise VCSException("Unable to checkout")
            return revision

        cmd = self.tc_vcs[:]
        cmd.extend(['revision', dest])
        return self.get_output_from_command(cmd, output_parser=parser)
