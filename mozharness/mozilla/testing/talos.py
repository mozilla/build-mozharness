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
import pprint
import re

from mozharness.base.config import parse_config_file
from mozharness.base.errors import PythonErrorList, TarErrorList
from mozharness.base.log import OutputParser, DEBUG, ERROR, CRITICAL, FATAL
from mozharness.base.script import BaseScript
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options, INSTALLER_SUFFIXES

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

class TalosOutputParser(OutputParser):
    minidump_regex = re.compile(r'''talosError: "error executing: '(\S+) (\S+) (\S+)'"''')
    minidump_output = None
    def parse_single_line(self, line):
        """ In Talos land, every line that starts with RETURN: needs to be
        printed with a TinderboxPrint:"""
        if line.startswith("RETURN:"):
            line.replace("RETURN:", "TinderboxPrint:")
        m = self.minidump_regex.search(line)
        if m:
            self.minidump_output = (m.group(1), m.group(2), m.group(3))
        super(TalosOutputParser, self).parse_single_line(line)

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
        [["--use-talos-json"],
          {"action": "store_true",
           "dest": "use_talos_json",
           "default": False,
           "help": "Use talos config from talos.json"
           }],
        [["--suite"],
          {"action": "store",
           "dest": "suite",
           "help": "Talos suite to run (from talos json)"
           }],
        [["--branch-name"],
          {"action": "store",
           "dest": "branch",
           "help": "Graphserver branch to report to"
           }],
        [["--system-bits"],
          {"action": "store",
           "dest": "system_bits",
           "type": "choice",
           "default": "32",
           "choices": ['32', '64'],
           "help": "Testing 32 or 64 (for talos json plugins)"
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
        self.talos_json_url = self.config.get("talos_json_url")
        self.talos_json = self.config.get("talos_json")
        self.talos_json_config = self.config.get("talos_json_config")
        self.tests = None
        self.pagesets_url = None
        self.pagesets_parent_dir_path = None
        self.pagesets_manifest_path = None
        if 'generate-config' in self.actions:
            self.preflight_generate_config()

    def query_talos_json_url(self):
        """Hacky, but I haven't figured out a better way to get the
        talos json url before we install the build.

        We can't get this information after we install the build, because
        we have to create the virtualenv to use mozinstall, and talos_url
        is specified in the talos json.
        """
        if self.talos_json_url:
            return self.talos_json_url
        self.info("Guessing talos json url...")
        if not self.installer_url:
            self.read_buildbot_config()
            self.postflight_read_buildbot_config()
            if not self.installer_url:
                self.fatal("Can't figure out talos_json_url without an installer_url!")
        for suffix in INSTALLER_SUFFIXES:
            if self.installer_url.endswith(suffix):
                build_txt_url = self.installer_url[:-len(suffix)] + '.txt'
                break
        else:
            self.fatal("Can't figure out talos_json_url from installer_url %s!" % self.installer_url)
        build_txt_file = self.download_file(build_txt_url, parent_dir=self.workdir)
        if not build_txt_file:
            self.fatal("Can't download %s to guess talos_json_url!" % build_txt_url)
        # HG hardcode?
        revision_re = re.compile(r'''([a-zA-Z]+://.+)/rev/([0-9a-fA-F]{10})''')
        contents = self.read_from_file(build_txt_file, error_level=FATAL).splitlines()
        for line in contents:
            m = revision_re.match(line)
            if m:
                break
        else:
            self.fatal("Can't figure out talos_json_url from %s!" % build_txt_file)
        self.talos_json_url = "%s/raw-file/%s/testing/talos/talos.json" % (m.group(1), m.group(2))
        return self.talos_json_url

    def download_talos_json(self):
        talos_json_url = self.query_talos_json_url()
        self.talos_json = self.download_file(talos_json_url,
                                             parent_dir=self.workdir,
                                             error_level=FATAL)

    def query_talos_json_config(self):
        """Return the talos json config; download and read from the
        talos_json_url if need be."""
        if self.talos_json_config:
            return self.talos_json_config
        c = self.config
        if not c['use_talos_json']:
            return
        if not c['suite']:
            self.fatal("To use talos_json, you must define use_talos_json, suite.")
            return
        if not self.talos_json:
            talos_json_url = self.query_talos_json_url()
            if not talos_json_url:
                self.fatal("Can't download talos_json without a talos_json_url!")
            self.download_talos_json()
        self.talos_json_config = parse_config_file(self.talos_json)
        self.info(pprint.pformat(self.talos_json_config))
        return self.talos_json_config

    def query_tests(self):
        """Determine if we have tests to run.

        Currently talos json will take precedence over config and command
        line options; if that's not a good default we can switch the order.
        """
        if self.tests is not None:
            return self.tests
        c = self.config
        if c['use_talos_json']:
            if not c['suite']:
                self.fatal("Can't use_talos_json without a --suite!")
            talos_config = self.query_talos_json_config()
            try:
                self.tests = talos_config['suites'][c['suite']]['tests']
            except KeyError, e:
                self.error("Badly formed talos_json for suite %s; KeyError trying to access talos_config['suites'][%s]['tests']: %s" % (c['suite'], c['suite'], str(e)))
        elif c['tests']:
            self.tests = c['tests']
        # Ignore these tests, specifically so we can not run a11yr on osx
        if c.get('ignore_tests'):
            for test in c['ignore_tests']:
                if test in self.tests:
                    del self.tests[self.tests.index(test)]
        return self.tests

    def query_talos_options(self):
        options = []
        c = self.config
        if self.query_talos_json_config():
            options += self.talos_json_config['suites'][c['suite']].get('talos_options', [])
        if c.get('talos_options'):
            options += c['talos_options']
        return options

    def query_talos_url(self):
        """Where do we install the talos python package from?
        This needs to be overrideable by the talos json.
        """
        if self.query_talos_json_config():
            return self.talos_json_config['global']['talos_url']
        else:
            return self.config.get('talos_url')

    def query_pagesets_url(self):
        """Certain suites require external pagesets to be downloaded and
        extracted.
        """
        if self.pagesets_url:
            return self.pagesets_url
        if self.query_talos_json_config():
            self.pagesets_url = self.talos_json_config['suites'][self.config['suite']].get('pagesets_url')
            return self.pagesets_url

    def query_pagesets_parent_dir_path(self):
        """ We have to copy the pageset into the webroot separately.

        Helper method to avoid hardcodes.
        """
        if self.pagesets_parent_dir_path:
            return self.pagesets_parent_dir_path
        if self.query_talos_json_config():
            self.pagesets_parent_dir_path = self.talos_json_config['suites'][self.config['suite']].get('pagesets_parent_dir_path')
            return self.pagesets_parent_dir_path

    def query_pagesets_manifest_path(self):
        """ We have to copy the tp manifest from webroot to talos root when
        those two directories aren't the same, until bug 795172 is fixed.

        Helper method to avoid hardcodes.
        """
        if self.pagesets_manifest_path:
            return self.pagesets_manifest_path
        if self.query_talos_json_config():
            self.pagesets_manifest_path = self.talos_json_config['suites'][self.config['suite']].get('pagesets_manifest_path')
            return self.pagesets_manifest_path

    def PerfConfigurator_options(self, args=None, **kw):
        """return options to PerfConfigurator"""
        # binary path
        binary_path = self.binary_path or self.config.get('binary_path')
        if not binary_path:
            self.fatal("Talos requires a path to the binary.  You can specify binary_path or add download-and-extract to your action list.")

        # talos options
        options = ['-v',] # hardcoded options (for now)
        if self.config.get('python_webserver', True):
            options.append('--develop')
        kw_options = {'output': 'talos.yml', # options overwritten from **kw
                      'executablePath': binary_path,
                      'results_url': self.results_url}
        kw_options['activeTests'] = self.query_tests()
        if self.config.get('title'):
            kw_options['title'] = self.config['title']
        if self.config.get('branch'):
            kw_options['branchName'] = self.config['branch']
        if self.symbols_path:
            kw_options['symbolsPath'] = self.symbols_path
        kw_options.update(kw)
        # talos expects tests to be in the format (e.g.) 'ts:tp5:tsvg'
        tests = kw_options.get('activeTests')
        if tests and not isinstance(tests, basestring):
            tests = ':'.join(tests) # Talos expects this format
            kw_options['activeTests'] = tests
        for key, value in kw_options.items():
            options.extend(['--%s' % key, value])
        # add datazilla results urls
        for url in self.config.get('datazilla_urls', []):
            options.extend(['--datazilla-url', url])
        # extra arguments
        if args is None:
            args = self.query_talos_options()
        options += args

        return options

    def talos_conf_path(self, conf):
        """return the full path for a talos .yml configuration file"""
        if os.path.isabs(conf):
            return conf
        return os.path.join(self.workdir, conf)

    def _populate_webroot(self):
        """Populate the production test slaves' webroots"""
        c = self.config
        talos_url = self.query_talos_url()
        if not c.get('webroot') or not talos_url:
            self.fatal("Both webroot and talos_url need to be set to populate_webroot!")
        self.info("Populating webroot %s..." % c['webroot'])
        talos_webdir = os.path.join(c['webroot'], 'talos')
        self.mkdir_p(c['webroot'], error_level=FATAL)
        self.rmtree(talos_webdir, error_level=FATAL)
        tarball = self.download_file(talos_url, parent_dir=self.workdir,
                                     error_level=FATAL)
        if self._is_windows():
            tarball = self.query_msys_path(tarball)
        command = c.get('webroot_extract_cmd')
        if command:
            command = command % {'tarball': tarball}
        else:
            tar = self.query_exe('tar', return_type='list')
            command = tar + ['zx', '--strip-components=1', '-f', tarball,
                             '**/talos/']
        self.run_command(command, cwd=c['webroot'],
                         error_list=TarErrorList, halt_on_failure=True)
        if c.get('use_talos_json'):
            if self.query_pagesets_url():
                self.info("Downloading pageset...")
                pagesets_path = os.path.join(c['webroot'], self.query_pagesets_parent_dir_path())
                self._download_unzip(self.pagesets_url, pagesets_path)
            plugins_url = self.talos_json_config['suites'][c['suite']].get('plugins', {}).get(c['system_bits'])
            if plugins_url:
                self.info("Downloading plugin...")
                # TODO add this path to talos.json ?
                self._download_unzip(plugins_url, os.path.join(talos_webdir, 'base_profile'))
            addons_urls = self.talos_json_config['suites'][c['suite']].get('talos_addons')
            if addons_urls:
                self.info("Downloading addons...")
                for addons_url in addons_urls:
                    self._download_unzip(addons_url, talos_webdir)


    # Action methods. {{{1
    # clobber defined in BaseScript
    # read_buildbot_config defined in BuildbotMixin

    def download_and_extract(self):
        super(Talos, self).download_and_extract()
        c = self.config
        if not c.get('python_webserver', True) and c.get('populate_webroot'):
            self._populate_webroot()

    def create_virtualenv(self, **kwargs):
        """VirtualenvMixin.create_virtualenv() assuemes we're using
        self.config['virtualenv_modules'].  Since we're overriding talos_url
        when using the talos json, we have to wrap that method here."""
        if self.query_talos_json_config():
            talos_url = self.query_talos_url()
            virtualenv_modules = self.config.get('virtualenv_modules', [])
            if 'talos' in virtualenv_modules:
                i = virtualenv_modules.index('talos')
                virtualenv_modules[i] = {'talos': talos_url}
                self.info(pprint.pformat(virtualenv_modules))
            return super(Talos, self).create_virtualenv(modules=virtualenv_modules)
        else:
            return super(Talos, self).create_virtualenv(**kwargs)

    def postflight_create_virtualenv(self):
        """ This belongs in download_and_install() but requires the
        virtualenv to be set up :(

        The real fix here may be a --tpmanifest option for PerfConfigurator.
        """
        c = self.config
        if not c.get('python_webserver', True) and c.get('populate_webroot') \
          and self.query_pagesets_url():
            pagesets_path = self.query_pagesets_manifest_path()
            manifest_source = os.path.join(c['webroot'], pagesets_path)
            manifest_target = os.path.join(self.query_python_site_packages_path(), pagesets_path)
            self.mkdir_p(os.path.dirname(manifest_target))
            self.copyfile(manifest_source, manifest_target)

    def preflight_generate_config(self):
        if not self.query_tests():
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
        command = [talos, '--noisy', '--debug', talos_conf_path]
        parser = TalosOutputParser(config=self.config, log_obj=self.log_obj,
                                   error_list=TalosErrorList)
        self.return_code = self.run_command(command, cwd=self.workdir,
                                            output_parser=parser)
        if parser.minidump_output:
            self.info("Looking at the minidump files for debugging purposes...")
            for item in parser.minidump_output:
                self.run_command(["ls", "-l", item])
