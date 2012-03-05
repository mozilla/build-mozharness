#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla.
#
# The Initial Developer of the Original Code is
# the Mozilla Foundation <http://www.mozilla.org/>.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Aki Sasaki <aki@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
'''Python usage, esp. virtualenv.
'''

import os

from mozharness.base.errors import PythonErrorList
from mozharness.base.log import WARNING, FATAL

# Virtualenv {{{1
virtualenv_config_options = [[
 ["--venv-path", "--virtualenv-path"],
 {"action": "store",
  "dest": "virtualenv_path",
  "default": "venv",
  "help": "Specify the path to the virtualenv top level directory"
 }
],
[["--virtualenv"],
 {"action": "store",
  "dest": "virtualenv",
  "help": "Specify the virtualenv executable to use"
  }
]]

class VirtualenvMixin(object):
    '''BaseScript mixin, designed to create and use virtualenvs.

    Config items:
     * virtualenv_path points to the virtualenv location on disk.
     * virtualenv_modules lists the module names.
     * MODULE_url list points to the module URLs (optional)
    Requires virtualenv to be in PATH.
    Depends on OSMixin
    '''
    python_paths = {}

    def query_virtualenv_path(self):
        c = self.config
        dirs = self.query_abs_dirs()
        if 'abs_virtualenv_dir' in dirs:
            return dirs['abs_virtualenv_dir']
        if os.path.isabs(c['virtualenv_path']):
            return c['virtualenv_path']
        return os.path.join(c['base_work_dir'], c['virtualenv_path'])

    def query_python_path(self, binary="python"):
        """Return the path of a binary inside the virtualenv, if
        c['virtualenv_path'] is set; otherwise return the binary name.
        Otherwise return None
        """
        if binary not in self.python_paths:
            bin_dir = 'bin'
            if self._is_windows():
                bin_dir = 'Scripts'
            virtualenv_path = self.query_virtualenv_path()
            if virtualenv_path:
                self.python_paths[binary] = os.path.abspath(os.path.join(virtualenv_path, bin_dir, binary))
            else:
                self.python_paths[binary] = self.query_exe(binary)
        return self.python_paths[binary]

    def query_package(self, package_name, error_level=WARNING):
        """
        Returns a list of all installed packages
        that contain package_name in their name
        """
        pip = self.query_python_path("pip")
        if not pip:
            self.log("query_package: Program pip not in path", level=error_level)
            return []
        output = self.get_output_from_command(pip + " freeze",
                                              silent=True)
        if not output:
            return []
        packages = output.split()
        return [package for package in packages
                if package.lower().find(package_name.lower()) != -1]

    def create_virtualenv(self):
        c = self.config
        dirs = self.query_abs_dirs()
        venv_path = self.query_virtualenv_path()
        self.info("Creating virtualenv %s" % venv_path)
        virtualenv = c.get('virtualenv', self.query_exe('virtualenv'))
        if isinstance(virtualenv, str):
            if not os.path.exists(virtualenv) and not self.which(virtualenv):
                self.add_summary("The executable '%s' is not found; not creating virtualenv!" % virtualenv, level=FATAL)
                return -1
            # allow for [python, virtualenv] in config
            virtualenv = [virtualenv]

        # https://bugs.launchpad.net/virtualenv/+bug/352844/comments/3
        # https://bugzilla.mozilla.org/show_bug.cgi?id=700415#c50
        if c.get('virtualenv_python_dll'):
            # We may someday want to copy a differently-named dll, but
            # let's not think about that right now =\
            dll_name = os.path.basename(c['virtualenv_python_dll'])
            target = self.query_python_path(dll_name)
            scripts_dir = os.path.dirname(target)
            self.mkdir_p(scripts_dir)
            self.copyfile(c['virtualenv_python_dll'], target)
        else:
            self.mkdir_p(dirs['abs_work_dir'])

        # make this list configurable?
        for module in ('distribute', 'pip'):
            if c.get('%s_url' % module):
                self.download_file(c['%s_url' % module],
                                   parent_dir=dirs['abs_work_dir'])

        virtualenv_options = c.get('virtualenv_options',
                                   ['--no-site-packages', '--distribute'])

        self.run_command(virtualenv + virtualenv_options + [venv_path],
                         cwd=dirs['abs_work_dir'],
                         error_list=PythonErrorList,
                         halt_on_failure=True)
        pip = self.query_python_path("pip")
        for module in c.get('virtualenv_modules', []):
            self.info("Installing %s into virtualenv %s" % (module, venv_path))
            self.run_command([pip, "install", c.get("%s_url" % module,
                                                    module)],
                             error_list=PythonErrorList,
                             halt_on_failure=True)
        self.info("Done creating virtualenv %s." % venv_path)



# __main__ {{{1

if __name__ == '__main__':
    '''TODO: unit tests.
    '''
    pass
