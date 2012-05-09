#!/usr/bin/env python

"""
Jetpack Performance Tests:
- https://wiki.mozilla.org/Auto-tools/Projects/JetPerf
- https://bugzilla.mozilla.org/show_bug.cgi?id=717036
"""

import copy
import os
import shutil
import sys
sys.path.insert(1, os.path.dirname(sys.path[0]))
from mozharness.base.script import BaseScript
from mozharness.base.vcs.mercurial import MercurialVCS
from mozharness.mozilla.testing.talos import Talos

# globals
repo = 'http://hg.mozilla.org/projects/addon-sdk' # addon-sdk repository

class JetPerf(Talos, MercurialVCS):
    """
    - Download the latest Add-on SDK
    - Download the test add-on sources
    - Build each test add-on with the add-ons SDK.
    - Run the talos tests on Firefox standalone and then with each of the
      built add-ons installed.
    """

    config_options = copy.deepcopy(Talos.config_options) + [
        [["--repo"],
         {'action': 'store',
          'dest': 'repo',
          'default': repo,
          'help': 'url of (hg) jetpack addon-sdk repository'
          }],
        [["--addon"],
         {'action': 'extend',
          'dest': 'addon-directories',
          'default': [],
          'help': "paths to addon directories",
          }],
        ]

    actions = ['clobber',
               'pull',
               'build',
               'read-buildbot-config',
               'download-and-extract',
               'create-virtualenv',
               'install',
               'test',
               'baseline'
               ]

    default_actions = ['clobber',
                       'pull',
                       'build',
                       'download-and-extract',
                       'create-virtualenv',
                       'install',
                       'test',
                       'baseline']

    def __init__(self, require_config_file=False):

        # initialize parent class
        Talos.__init__(self,
                       config={'tests': ['ts']},
                       all_actions=self.actions,
                       default_actions=self.default_actions,
                       require_config_file=require_config_file)

        # set instance defaults
        self.addon_sdk = os.path.join(self.workdir, 'addon-sdk')
        self.addonsdir = os.path.join(self.workdir, 'addons')

        # ensure we have tests
        self.preflight_generate_config()

    def pull(self):
        """clone the jetpack repository"""

        MercurialVCS.clone(self, self.config['repo'], self.addon_sdk)

    def cfx(self):
        """returns path to cfx"""
        path = os.path.join(self.addon_sdk, 'bin', 'cfx')
        if not os.path.exists(path):
            return None
        return path

    def build(self):
        """Build each test add-on with the add-ons SDK"""

        cfx = self.cfx()
        if not cfx:
            # clone the addon-sdk if needed
            self.fatal("%s not found; make sure you clone the addon-sdk repo first" % cfx)

        # TODO: pull from hg if specified
        addons = self.config['addon-directories']
        if not addons:
            self.error("No addons supplied")

        # ensure the addons are unique
        basenames = set([os.path.basename(addon) for addon in addons])
        if len(basenames) < len(addons):
            self.error("Addon directories must have unique basenames")

        # ensure that all addons exist
        missing = [i for i in addons if not os.path.exists(i)]
        if missing:
            self.error("Missing addon(s): %s" % ', '.join(missing))

        # build the addons
        self.rmtree(self.addonsdir)
        self.mkdir_p(self.addonsdir)
        for addon in addons:

            # copy the addons to workdir so as not to tamper with the source
            addon = os.path.normpath(addon)
            package = os.path.basename(addon)
            path = os.path.join(self.addonsdir, package)
            if os.path.exists(path):
                self.rmtree(path)
            shutil.copytree(addon, path)

            # - package to .xpi:
            for ctr in range(2):
                # - run twice to avoid:
                # """
                # No 'id' in package.json: creating a new ID for you.
                # package.json modified: please re-run 'cfx xpi'
                # """
                # see https://bugzilla.mozilla.org/show_bug.cgi?id=613587
                code = self.run_command([cfx, 'xpi'], cwd=path)
                if code:
                    self.fatal("Error creating xpi file")
            xpi = os.path.join(path, '%s.xpi' % package)
            if not os.path.exists(xpi):
                self.fatal("'%s' not found; 'cfx xpi' did not work" % xpi)

            # TODO:
            # - verify package.json exists for the addons
            # - read the addon name from package.json

    def run_talos(self, name, *args, **kw):
        """
        runs PerfConfigurator and talos
        """

        # .yml file name
        yml = '%s.yml' % name

        # get PerfConfigurator options
        args = list(args)
        args += self.config.get('talos_options', [])
        options = self.PerfConfigurator_options(args=args, output=yml, **kw)

        # run PerfConfigurator
        self.generate_config(conf=yml, options=options)

        # run talos
        self.run_tests(conf=yml)

    def test(self):
        """run talos tests"""

        # locate the .xpi files
        xpis = []
        for directory in os.listdir(self.addonsdir):
            path = os.path.join(self.addonsdir, directory)
            if not os.path.isdir(path):
                continue
            _xpis = [i for i in os.listdir(path)
                     if i.endswith('.xpi')]
            if not len(_xpis):
                continue
            if len(_xpis) > 1:
                self.warning("More than one addon found in %s: %s" % (path, _xpis))
            xpis.extend([os.path.join(directory, xpi) for xpi in _xpis])
        if not xpis:
            self.fatal("No addons found in %s" % self.addonsdir)

        # run talos
        args = []
        for xpi in xpis:
            args.extend(['--extension', xpi])
        self.run_talos('jetperf', *args)

        # print the results file location if it is a file
        if self.results_url.startswith('file://'):
            filename = self.results_url[len('file://'):]
            if not os.path.exists(filename):
                self.fatal("Results file not found: %s" % filename)

    def baseline_results_filename(self):
        return os.path.join(self.workdir, 'baseline.txt')

    def baseline(self):
        """run baseline ts tests"""
        args = []
        filename = self.baseline_results_filename()
        if os.path.exists(filename):
            self.rmtree(filename)
        self.run_talos('baseline', results_url='file://%s' % filename)
        if not os.path.exists(filename):
            self.fatal("Results file not found: %s" % filename)


def main(args=sys.argv[1:]):
    """CLI entry point"""
    jetperf = JetPerf()
    jetperf.run()

if __name__ == '__main__':
    main()
