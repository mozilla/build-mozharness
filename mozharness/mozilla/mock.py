#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Code to integrate with mock
"""

import subprocess

# MockMixin {{{1
class MockMixin(object):
    """Provides methods to setup and interact with mock environments.
    https://wiki.mozilla.org/ReleaseEngineering/Applications/Mock

    This is dependent on ScriptMixin
    """
    done_mock_setup = False
    mock_enabled = False

    def init_mock(self, mock_target):
        "Initialize mock environment defined by `mock_target`"
        cmd = ['mock_mozilla', '-r', mock_target, '--init']
        return super(MockMixin, self).run_command(cmd, halt_on_failure=True)

    def install_mock_packages(self, mock_target, packages):
        "Install `packages` into mock environment `mock_target`"
        cmd = ['mock_mozilla', '-r', mock_target, '--install'] + packages
        # TODO: parse output to see if packages actually were installed
        return super(MockMixin, self).run_command(cmd, halt_on_failure=True)

    def copy_mock_files(self, mock_target, files):
        """Copy files into the mock environment `mock_target`. `files` should
        be an iterable of 2-tuples: (src, dst)"""
        cmd_base = ['mock_mozilla', '-r', mock_target, '--copyin', '--unpriv']
        for src, dest in files:
            cmd = cmd_base + [src, dest]
            super(MockMixin, self).run_command(cmd, halt_on_failure=True)
            super(MockMixin, self).run_command(
                    ['mock_mozilla', '-r', mock_target, '--shell',
                     'chown -R mock_mozilla %s' % dest],
                    halt_on_failure=True)

    def enable_mock(self):
        """Wrap self.run_command and self.get_output_from_command to run inside
        the mock environment given by self.config['mock_target']"""
        if not 'mock_target' in self.config:
            return
        self.mock_enabled = True
        self.run_command = self.run_command_m
        self.get_output_from_command = self.get_output_from_command_m

    def disable_mock(self):
        """Restore self.run_command and self.get_output_from_command to their
        original versions. This is the opposite of self.enable_mock()"""
        if not 'mock_target' in self.config:
            return
        self.mock_enabled = False
        self.run_command = super(MockMixin, self).run_command
        self.get_output_from_command = super(MockMixin, self).get_output_from_command

    def _do_mock_command(self, func, mock_target, command, cwd=None, env=None, **kwargs):
        """Internal helper for preparing commands to run under mock. Used by
        run_mock_command and get_mock_output_from_command."""
        cmd = ['mock_mozilla', '-r', mock_target, '-q']
        if cwd:
            cmd += ['--cwd', cwd]

        cmd += ['--unpriv', '--shell']

        if not isinstance(command, basestring):
            command = subprocess.list2cmdline(command)

        # XXX - Hack - gets around AB_CD=%(locale)s type arguments
        command = command.replace("(", "\\(")
        command = command.replace(")", "\\)")

        if env:
            env_cmd = ['/usr/bin/env']
            for key, value in env.items():
                # $HOME won't work inside the mock chroot
                if key == 'HOME':
                    continue
                value = value.replace(";", "\\;")
                env_cmd += ['%s=%s' % (key, value)]
            cmd.append(subprocess.list2cmdline(env_cmd) + " " + command)
        else:
            cmd.append(command)
        return func(cmd, cwd=cwd, **kwargs)

    def run_mock_command(self, mock_target, command, cwd=None, env=None, **kwargs):
        """Same as ScriptMixin.run_command, except runs command inside mock
        environment `mock_target`."""
        return self._do_mock_command(
                super(MockMixin, self).run_command,
                mock_target, command, cwd, env, **kwargs)

    def get_mock_output_from_command(self, mock_target, command, cwd=None, env=None, **kwargs):
        """Same as ScriptMixin.get_output_from_command, except runs command
        inside mock environment `mock_target`."""
        return self._do_mock_command(
                super(MockMixin, self).get_output_from_command,
                mock_target, command, cwd, env, **kwargs)

    def setup_mock(self, mock_target=None, mock_packages=None, mock_files=None):
        """Initializes and installs packages, copies files into mock
        environment given by configuration in self.config.  The mock
        environment is given by self.config['mock_target'], the list of packges
        to install given by self.config['mock_packages'], and the list of files
        to copy in is self.config['mock_files']."""
        if self.done_mock_setup:
            return

        c = self.config

        if mock_target is None:
            assert 'mock_target' in c
            t = c['mock_target']
        else:
            t = mock_target
        self.init_mock(t)

        if mock_packages is None:
            mock_packages = list(c.get('mock_packages'))
        if mock_packages:
            self.install_mock_packages(t, mock_packages)

        if mock_files is None:
            mock_files = list(c.get('mock_files'))
        if mock_files:
            self.copy_mock_files(t, mock_files)

        self.done_mock_setup = True

    def run_command_m(self, *args, **kwargs):
        """Executes self.run_mock_command if self.config['mock_target'] is set,
        otherwise executes self.run_command."""
        if 'mock_target' in self.config:
            self.setup_mock()
            return self.run_mock_command(self.config['mock_target'], *args, **kwargs)
        else:
            return super(MockMixin, self).run_command(*args, **kwargs)

    def get_output_from_command_m(self, *args, **kwargs):
        """Executes self.get_mock_output_from_command if
        self.config['mock_target'] is set, otherwise executes
        self.get_output_from_command."""
        if 'mock_target' in self.config:
            self.setup_mock()
            return self.get_mock_output_from_command(self.config['mock_target'], *args, **kwargs)
        else:
            return super(MockMixin, self).get_output_from_command(*args, **kwargs)
