#!/usr/bin/env python

"""
run talos test suites in a virtualenv
"""

import os

from mozharness.base.python import virtualenv_config_options, VirtualenvMixin
from mozharness.base.script import BaseScript

class Talos(VirtualenvMixin, BaseScript):
    """
    install and run Talos tests:
    https://wiki.mozilla.org/Buildbot/Talos
    """

    config_options = [
        [["--title"],
         {"action": "store",
          "dest": "title",
          "default": None,
          "help": "talos run title"}],
        [["--talos-url"],
         {"action": "store",
          "dest": "talos_url",
          "default": "http://hg.mozilla.org/build/talos/archive/tip.tar.gz",
          "help": "Specify the talos package url"
          }],
        [["--talos-branch"],
         {"action": "store",
          "dest": "talos_branch",
          "default": "Mozilla-Central",
          "help": "Specify the branch name",
          }],
        [["--pyyaml-url"],
         {"action": "store",
          "dest": "pyyaml_url",
          "default": "http://pypi.python.org/packages/source/P/PyYAML/PyYAML-3.10.tar.gz", # note that this is subject to package-rot
          "help": "URL to PyYAML package"
          }],
        [["--pageloader-url"],
         {"action": "store",
          "dest": "pageloader_url",
          "default": "http://hg.mozilla.org/build/pageloader/archive/tip.zip",
          "help": "URL to PageLoader extension"
          }],
        [["-a", "--activeTests"],
         {"action": "extend",
          "dest": "activeTests",
          "default": [],
          "help": "Specify the tests to run"
          }],
        [["--appname"],
         {"action": "store",
          "dest": "appname",
          "default": None,
          "help": "Path to the Firefox binary to run tests on",
          }],
        [["--add-options"],
          {"action": "extend",
           "dest": "addOptions",
           "default": None,
           "help": "extra options to PerfConfigurator"
           }],
        ] + virtualenv_config_options

    def __init__(self, require_config_file=False):
        BaseScript.__init__(self,
                            config_options=self.config_options,
                            all_actions=['clobber',
                                         'create-virtualenv',
                                         'install-pageloader',
                                         'generate-config',
                                         'run-tests'
                                         ],
                            default_actions=['clobber',
                                             'create-virtualenv',
                                             'install-pageloader',
                                             'generate-config',
                                             'run-tests'
                                             ],
                            require_config_file=require_config_file,
                            config={"virtualenv_modules": ["pyyaml", "talos"]},
                            )

    def _set_talos_dir(self):
        """XXX this is required as talos must be run out of its directory"""
        python = self.query_python_path()
        self.talos_dir = self.get_output_from_command([python, '-c', 'import os, talos; print os.path.dirname(os.path.abspath(talos.__file__))'])
        if not self.talos_dir:
            self.fatal("Talos directory could not be found")
        self.info('Talos directory: %s' % self.talos_dir)

    def install_pageloader(self):
        """install pageloader"""
        if not hasattr(self, 'talos_dir'):
            self._set_talos_dir()
        dest = os.path.join(self.talos_dir, 'page_load_test', 'pageloader.xpi')
        self.download_file(self.config['pageloader_url'], dest)

    def generate_config(self):
        """generate talos configuration"""

        firefox = self.config.get('appname')
        if not firefox:
            self.fatal("No appname specified; please specify --appname")
        firefox = os.path.abspath(firefox)
        tests = self.config['activeTests']
        if not tests:
            self.fatal("No tests specified; please specify --activeTests")
        tests = ':'.join(tests) # Talos expects this format
        if not hasattr(self, 'talos_dir'):
            self._set_talos_dir()
        python = self.query_python_path()
        command = [python, 'PerfConfigurator.py', '-v', '-e', firefox, '-a', tests, '--output', 'talos.yml', '-b', self.config['talos_branch'], '--branchName', self.config['talos_branch']]
        if self.config.get('title'):
            command += ["-t", self.config['title']]
        if self.config.get('addOptions'):
            command += self.config['addOptions']
        self.run_command(command, cwd=self.talos_dir)
        self.talos_conf = os.path.join(self.talos_dir, 'talos.yml')

    def run_tests(self):
        if not hasattr(self, 'talos_conf'):
            self.generate_config()

        # run talos tests
        # assumes a webserver is appropriately running
        python = self.query_python_path()
        self.return_code = self.run_command([python, 'run_tests.py', '--noisy', self.talos_conf], cwd=self.talos_dir)


if __name__ == '__main__':
    talos = Talos()
    talos.run()
