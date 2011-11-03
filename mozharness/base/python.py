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
from mozharness.base.log import DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, IGNORE

# Virtualenv {{{1
virtualenv_config_options = [[
 ["--venv-path", "--virtualenv-path"],
 {"action": "store",
  "dest": "virtualenv_path",
  "default": os.path.join(os.getcwd(), "venv"),
  "help": "Specify the virtualenv path"
 }
]]

class VirtualenvMixin(object):
    '''BaseScript mixin, designed to create and use virtualenvs.

    Config items:
     * virtualenv_path points to the virtualenv location on disk.
     * virtualenv_modules lists the module names.
     * MODULE_url list points to the module URLs (optional)
    Requires virtualenv to be in PATH.
    '''
    python_paths = {}

    def query_python_path(self, binary="python"):
        """Return the path of a binary inside the virtualenv, if
        c['virtualenv_path'] is set; otherwise return the binary name.
        """
        if binary not in self.python_paths:
            bin_dir = 'bin'
            if self._is_windows():
                bin_dir = 'Scripts'
            if self.config.get('virtualenv_path'):
                self.python_paths[binary] = os.path.abspath(os.path.join(self.config['virtualenv_path'], bin_dir, binary))
            else:
                self.python_paths[binary] = binary
        return self.python_paths[binary]

    def create_virtualenv(self):
        c = self.config
        if not c.get('virtualenv_path'):
            self.add_summary("No virtualenv specified; not creating virtualenv!", level=FATAL)
            return -1
        venv_path = os.path.abspath(c['virtualenv_path'])
        self.info("Creating virtualenv %s" % venv_path)
        self.run_command(["virtualenv", "--no-site-packages",
                          venv_path],
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
