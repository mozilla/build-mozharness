#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""
run talos tests in a virtualenv
"""

import os
import re

from mozharness.base.errors import PythonErrorList
from mozharness.base.log import DEBUG, ERROR, CRITICAL
from mozharness.base.script import BaseScript
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options

TalosErrorList = PythonErrorList + [
 {'regex': re.compile(r'''run-as: Package '.*' is unknown'''), 'level': DEBUG},
 {'substr': r'''FAIL: Graph server unreachable''', 'level': CRITICAL},
 {'substr': r'''FAIL: Busted:''', 'level': CRITICAL},
 {'substr': r'''FAIL: failed to cleanup''', 'level': ERROR},
 {'substr': r'''erfConfigurator.py: Unknown error''', 'level': CRITICAL},
 {'substr': r'''talosError''', 'level': CRITICAL},
 {'regex': re.compile(r'''No machine_name called '.*' can be found'''), 'level': CRITICAL},
 {'substr': r"""No such file or directory: 'browser_output.txt'""",
  'level': CRITICAL,
  'explanation': r"""Most likely the browser failed to launch, or the test was otherwise unsuccessful in even starting."""},
]

# TODO: check for running processes on script invocation

class Talos(TestingMixin, BaseScript):
    """
    install and run Talos tests:
    https://wiki.mozilla.org/Buildbot/Talos
    """

    talos_options = [
        [["-a", "--tests"],
         {'action': 'extend',
          "dest": "tests",
          "default": [],
          "help": "Specify the tests to run"
          }],
        [["--results-url"],
         {'action': 'store',
          'dest': 'results_url',
          'default': None,
          'help': "URL to send results to"
          }],
        ]

    config_options = [
        [["--talos-url"],
         {"action": "store",
          "dest": "talos_url",
          "default": "http://hg.mozilla.org/build/talos/archive/tip.tar.gz",
          "help": "Specify the talos package url"
          }],
        [["--add-option"],
          {"action": "extend",
           "dest": "talos_options",
           "default": None,
           "help": "extra options to PerfConfigurator"
           }],
        ] + talos_options + testing_config_options

    def __init__(self, **kwargs):
        kwargs.setdefault('config_options', self.config_options)
        kwargs.setdefault('all_actions', ['clobber',
                                          'read-buildbot-config',
                                          'download-and-extract',
                                          'create-virtualenv',
                                          'install',
                                          'generate-config',
                                          'run-tests',
                                         ])
        kwargs.setdefault('default_actions', ['clobber',
                                              'download-and-extract',
                                              'create-virtualenv',
                                              'install',
                                              'generate-config',
                                              'run-tests',
                                             ])
        kwargs.setdefault('config', {})
        kwargs['config'].setdefault('virtualenv_modules', ["talos", "mozinstall"])
        BaseScript.__init__(self, **kwargs)

        self.workdir = self.query_abs_dirs()['abs_work_dir'] # convenience

        # results output
        self.results_url = self.config.get('results_url')
        if self.results_url is None:
            # use a results_url by default based on the class name in the working directory
            self.results_url = 'file://%s' % os.path.join(self.workdir, self.__class__.__name__.lower() + '.txt')
        self.installer_url = self.config.get("installer_url")

    def _pre_config_lock(self, rw_config):
        """setup and sanity check"""

        if 'generate-config' in self.actions:
            self.preflight_generate_config()

    def PerfConfigurator_options(self, args=None, **kw):
        """return options to PerfConfigurator"""

        # binary path
        binary_path = self.binary_path or self.config.get('binary_path')
        if not binary_path:
            self.fatal("Talos requires a path to the binary")

        # talos options
        options = ['-v', '--develop'] # hardcoded options (for now)
        kw_options = {'output': 'talos.yml', # options overwritten from **kw
                      'executablePath': binary_path,
                      'activeTests': self.tests,
                      'results_url': self.results_url}
        if self.config.get('title'):
            kw_options['title'] = self.config['title']
        kw_options.update(kw)

        # talos expects tests to be in the format (e.g.) 'ts:tp5:tsvg'
        tests = kw_options['activeTests']
        if not isinstance(tests, basestring):
            tests = ':'.join(tests) # Talos expects this format
            kw_options['activeTests'] = tests

        for key, value in kw_options.items():
            options.extend(['--%s' % key, value])

        # extra arguments
        if args is None:
            args = self.config.get('talos_options', [])
        options += args

        return options

    def talos_conf_path(self, conf):
        """return the full path for a talos .yml configuration file"""
        if os.path.isabs(conf):
            return conf
        return os.path.join(self.workdir, conf)

    def preflight_generate_config(self):

        # Talos tests to run
        self.tests = self.config['tests']
        if not self.tests:
            self.fatal("No tests specified; please specify --tests")

    def generate_config(self, conf='talos.yml', options=None):
        """generate talos configuration"""
        # XXX note: conf *must* match what is in options, if the latter is given

        # find the path to the talos .yml configuration
        # and remove if it exists
        talos_conf_path = self.talos_conf_path(conf)
        if os.path.exists(talos_conf_path):
            os.remove(talos_conf_path)

        # find PerfConfigurator console script
        # TODO: support remotePerfConfigurator if
        # https://bugzilla.mozilla.org/show_bug.cgi?id=704654
        # is not fixed first
        PerfConfigurator = self.query_python_path('PerfConfigurator')
        if not os.path.exists(PerfConfigurator):
            self.fatal("PerfConfigurator not found")

        # get command line for PerfConfigurator
        if options is None:
            options = self.PerfConfigurator_options(output=talos_conf_path)
        command = [PerfConfigurator] + options

        # run PerfConfigurator and ensure conf creation
        self.run_command(command, cwd=self.workdir,
                         error_list=TalosErrorList)
        if not os.path.exists(talos_conf_path):
            self.fatal("PerfConfigurator invokation failed: configuration file '%s' not found" % talos_conf_path)

    def run_tests(self, conf='talos.yml'):

        # generate configuration if necessary
        talos_conf_path = self.talos_conf_path(conf)
        if not os.path.exists(talos_conf_path):
            self.generate_config(conf)

        # run talos tests
        talos = self.query_python_path('talos')
        if not os.path.exists(talos):
            self.fatal("talos script not found")
        command = [talos, '--noisy', talos_conf_path]
        self.return_code = self.run_command(command, cwd=self.workdir,
                                            error_list=TalosErrorList)
