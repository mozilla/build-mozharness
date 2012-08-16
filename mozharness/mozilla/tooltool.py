from mozharness.base.errors import PythonErrorList


class TooltoolMixin(object):
    """Mixin class for handling tooltool manifests.
    Requires self.config['tooltool_servers'] to be a list of base urls
    """
    def tooltool_fetch(self, manifest, output_dir=None):
        """docstring for tooltool_fetch"""
        tooltool = self.query_exe('tooltool.py', return_type='list')
        cmd = tooltool
        for s in self.config['tooltool_servers']:
            cmd.extend(['--url', s])
        cmd.extend(['fetch', '-m', manifest, '-o'])
        self.run_command(cmd, cwd=output_dir, error_list=PythonErrorList)
