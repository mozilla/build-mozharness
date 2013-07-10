#!/usr/bin/env python -u
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""device_talosrunner.py

Set up and run talos against a device running SUT Agent or ADBD.

WIP.
"""

import os
import sys
import time

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import PythonErrorList
from mozharness.mozilla.testing.device import device_config_options, DeviceMixin
from mozharness.mozilla.testing.talos import Talos

# Stop buffering!
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

# DeviceTalosRunner {{{1
class DeviceTalosRunner(DeviceMixin, Talos):
    config_options = Talos.config_options + device_config_options

    def __init__(self, require_config_file=False):
        super(DeviceTalosRunner, self).__init__(
         config_options=self.config_options,
         all_actions=['preclean',
                      'create-virtualenv',
                      'check-device',
                      'read-buildbot-config',
                      'download',
                      'unpack',
                      'pre-cleanup-device',
                      'install-app',
                      'generate-config',
                      'run-tests',
                      'post-cleanup-device',
#                      'upload',
#                      'notify',
#                      'postclean',
#                      'reboot-host',
                      ],
         default_actions=['preclean',
                          'create-virtualenv',
                          'check-device',
                          'pre-cleanup-device',
                          'download',
                          'unpack',
                          'install-app',
                          'generate-config',
                          'run-tests',
                          'post-cleanup-device',
                         ],
         config={'virtualenv_modules': ['talos']},
         require_config_file=require_config_file,
        )
        if not self.installer_path:
            self.installer_path = os.path.join(self.workdir, 'installer.apk')

    def _pre_config_lock(self, rw_config):
        super(DeviceTalosRunner, self)._pre_config_lock(rw_config)
        if 'device_protocol' not in self.config:
            self.fatal("Must specify --device-protocol!")

    # Helper methods {{{2

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(DeviceTalosRunner, self).query_abs_dirs()
        abs_dirs['abs_application_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                                                       'application')
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    # Actions {{{2

    def preclean(self):
        self.clobber()

    # create_virtualenv defined in VirtualenvMixin
    # check_device defined in DeviceMixin

    def pre_cleanup_device(self):
        self.cleanup_device()

    # read_buildbot_config defined in BuildbotMixin

    def download(self):
        if not self.installer_url:
            self.installer_url = self.config['installer_url']
        self._download_installer()

    def unpack(self):
        # We need a generic extract() again.
        dirs = self.query_abs_dirs()
        unzip = self.query_exe("unzip")
        unzip_cmd = [unzip, '-q', self.installer_path]
        self.mkdir_p(dirs['abs_application_dir'])
        self.run_command(unzip_cmd, cwd=dirs['abs_application_dir'])
        inifile = os.path.join(dirs['abs_application_dir'], 'application.ini')
        remoteappini = os.path.join(dirs['abs_work_dir'], 'remoteapp.ini')
        self.copyfile(inifile, remoteappini)

    # TODO install_app defined in DeviceMixin

    def preflight_generate_config(self):
        if 'install-app' in self.actions:
            c = self.config
            time_to_sleep = c.get("post_install_sleep", 60)
            self.info("Sleeping %d to avoid post-install errors" %
                      time_to_sleep)
            time.sleep(time_to_sleep)

        super(DeviceTalosRunner, self).preflight_generate_config()

    def generate_config(self, conf='talos.yml', options=None):
        c = self.config
        dirs = self.query_abs_dirs()
        python = self.query_python_path()
        script_dir = os.path.dirname(python)
        additional_options = []
        if c.get('disable_chrome'):
            additional_options.append("--noChrome")
        if c['device_protocol'] == 'sut':
            additional_options.extend(['--remoteDevice', c['device_ip']])
            additional_options.extend(['--remotePort', c.get('device_port', '20701')])
        elif c['device_protocol'] == 'adb':
            additional_options.extend(['--remoteDevice', ''])
            additional_options.extend(['--remotePort', '-1'])
        if c.get('start_python_webserver'):
            additional_options.append('--develop')
#        if c.get('repository'):
#            additional_options.append('repository', c['repository'])
        script = os.path.join(script_dir, 'remotePerfConfigurator')
        # TODO set no_chrome based on active tests
        command = [script,
                   '-v',
                   '-e', c['device_package_name'],
                   '-t', c.get('talos_device_name', c['device_name']),
                   '--branchName', c['talos_branch'],
                   '--resultsServer', c['graph_server'],
                   '--resultsLink', c['results_link'],
                   '--activeTests', ':'.join(c['talos_suites']),
                   '--sampleConfig', c['talos_config_file'],
                   '--output', conf,
                   '--browserWait', '60',
                   '--webServer', c['talos_webserver'],
                  ] + additional_options
        self.run_command(command, cwd=dirs['abs_work_dir'],
                         error_list=PythonErrorList,
                         halt_on_failure=True)

#    def preflight_run_talos(self):
#        #TODO get this un-adb-hardcoded
#        if 'install-app' not in self.actions:
#            c = self.config
#            device_id = self.query_device_id()
#            adb = self.query_exe('adb')
#            kill = self.query_device_exe('kill')
#            procs = self.get_output_from_command([adb, "-s", device_id,
#                                                  'shell', 'ps'],
#                                                 log_level=DEBUG)
#            if c['device_package_name'] in procs:
#                self.info("Found %s running... attempting to kill." %
#                          c['device_package_name'])
#                # TODO this needs to kill the pid
#                # TODO verify it's gone
#                for line in procs.splitlines():
#                    line_contents = re.split('\s+', line)
#                    if line_contents[-1].startswith(c['device_package_name']):
#                        self.run_command([adb, "-s", device_id, 'shell',
#                                          kill, line_contents[1]],
#                                         error_list=ADBErrorList)

    def post_cleanup_device(self):
        c = self.config
        if c.get('enable_automation'):
            self.cleanup_device(reboot=True)
        else:
            self.info("Nothing to do without enable_automation set.")

    # run_tests() is in Talos

# __main__ {{{1
if __name__ == '__main__':
    device_talos_runner = DeviceTalosRunner()
    device_talos_runner.run_and_exit()
