#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import os
import sys
from time import sleep, time

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_FAILURE, TBPL_WARNING, TBPL_RETRY, BuildbotMixin
from mozharness.base.log import INFO, ERROR
from mozharness.base.python import VirtualenvMixin
from mozharness.base.script import BaseScript
from mozharness.mozilla.testing.testbase import TestingMixin
from mozharness.mozilla.testing.unittest import TestSummaryOutputParserHelper
from mozharness.mozilla.testing.mozpool import MozpoolMixin, MozpoolConflictException, MozpoolException

#TODO - adjust these values
MAX_RETRIES = 20
RETRY_INTERVAL = 60
REQUEST_DURATION = 60 * 40

class PandaTest(TestingMixin, BaseScript, VirtualenvMixin, MozpoolMixin, BuildbotMixin):
    config_options = [
        [["--mozpool-api-url"], {
            "dest": "mozpool_api_url",
            "help": "Override mozpool api url",
        }],
        [["--mozpool-device"], {
            "dest": "mozpool_device",
            "help": "Set Panda device to run tests on",
        }],
        [["--mozpool-assignee"], {
            "dest": "mozpool_assignee",
            "help": "Set mozpool assignee (requestor name, free-form)",
        }],
        [["--mozpool-b2gbase"], {
            "dest": "mozpool_b2gbase",
            "help": "Set b2gbase url",
        }],
        [["--test-type"], {
            "dest": "test_type",
            "default": "b2g",
            "help": "Specifies the --type parameter to pass to Marionette",
        }],
    ]

    error_list = []

    mozbase_dir = os.path.join('tests', 'mozbase')
    virtualenv_modules = [
        'requests',
        'mozinstall',
        { 'marionette': os.path.join('tests', 'marionette/client') },
        { 'gaiatest': os.path.join('tests', 'gaiatest') },
    ]

    def __init__(self, require_config_file=False):
        super(PandaTest, self).__init__(
            config_options=self.config_options,
            all_actions=['clobber',
                         'read-buildbot-config',
                         'download-and-extract',
                         'create-virtualenv',
                         'request-device',
                         'run-test',
                         'close-request'],
            default_actions=['clobber',
                             'create-virtualenv',
                             'download-and-extract',
                             'request-device',
                             'run-test',
                             'close-request'],
            require_config_file=require_config_file,
            config={'virtualenv_modules': self.virtualenv_modules,
                    'require_test_zip': True,})

        self.foopyname = self.query_env()["HOSTNAME"].split(".")[0]
        self.mozpool_assignee = self.config.get('mozpool_assignee', \
                self.foopyname)
        self.request_url = None

    def postflight_read_buildbot_config(self):
        super(PandaTest, self).postflight_read_buildbot_config()
        self.mozpool_device = self.config.get('mozpool_device', \
                self.buildbot_config.get('properties')["slavename"])

    def request_device(self):
        mph = self.query_mozpool_handler(self.mozpool_device)
        for retry in self._retry_sleep(sleep_time=RETRY_INTERVAL, max_retries=MAX_RETRIES,
                error_message="INFRA-ERROR: Could not request device '%s'" % self.mozpool_device,
                tbpl_status=TBPL_RETRY):
            try:
                duration = REQUEST_DURATION
                image = 'b2g'
                b2gbase = self.config.get('mozpool_b2g_base', \
                        self.installer_url)

                response = mph.request_device(self.mozpool_device, self.mozpool_assignee, image, duration, \
                               b2gbase=b2gbase, pxe_config=None)
                break
            except MozpoolConflictException:
                self.warning("Device unavailable. Retry#%i.." % retry)
            except MozpoolException, e:
                self.buildbot_status(TBPL_RETRY)
                self.fatal("We could not request the device: %s" % str(e))

        self.request_url = response['request']['url']
        self.info("Got request, url=%s" % self.request_url)
        self._wait_for_request_ready()

    def run_test(self):
        """
        Run the Panda tests
        """
        level = INFO
        env = self.query_env()
        env["DM_TRANS"] = "sut"
        env["TEST_DEVICE"] = self.mozpool_device
        mph = self.query_mozpool_handler(self.mozpool_device)
        sys.path.append(self.query_python_site_packages_path())
        from mozdevice.devicemanagerSUT import DeviceManagerSUT
        APP_INI_LOCATION = '/system/b2g/application.ini'
        dm = None
        try:
            self.info("Connecting to: %s" % self.mozpool_device)
            dm = DeviceManagerSUT(self.mozpool_device)
        except Exception, e:
            self.error("%s" % str(e))
            mph.close_request(self.request_url)
            self.buildbot_status(TBPL_RETRY)
            self.fatal("ERROR: Unable to properly connect to SUT Port on device.")
        # No need for 300 second SUT socket timeouts here
        dm.default_timeout = 30
        if not dm.fileExists(APP_INI_LOCATION):
            mph.close_request(self.request_url)
            self.buildbot_status(TBPL_RETRY)
            self.fatal("ERROR: expected file (%s) not found" % APP_INI_LOCATION)
        file_contents = dm.catFile(APP_INI_LOCATION)
        if file_contents is None:
            mph.close_request(self.request_url)
            self.buildbot_status(TBPL_RETRY)
            self.fatal("ERROR: Unable to read file (%s)" % APP_INI_LOCATION)
        self.info("Read of file (%s) follows" % APP_INI_LOCATION)
        self.info("===========================")
        self.info(file_contents)

        dm._runCmds([{ 'cmd': 'setutime %s' % int(time())}])
        device_time = dm._runCmds([{ 'cmd': 'clok'}])
        self.info("Current time on device: %s - %s" % \
            (device_time, time.strftime("%x %H:%M:%S", time.gmtime(device_time))))

        self.info("Running tests...")
        dirs = self.query_abs_dirs()
        cmd = [self.query_python_path('gaiatest'),
               '--address', '%s:2828' % self.mozpool_device,
               '--type', self.config['test_type'],
               os.path.join(dirs['abs_gaiatest_dir'], 'tests', 'manifest.ini')]
        test_summary_parser = TestSummaryOutputParserHelper(config=self.config, log_obj=self.log_obj)

        code = self.run_command(cmd, env=env, output_parser=test_summary_parser)
        if code == 0:
            tbpl_status = TBPL_SUCCESS
        elif code == 10: # XXX assuming this code is the right one
            tbpl_status = TBPL_WARNING
        else:
            level = ERROR
            tbpl_status = TBPL_FAILURE

        test_summary_parser.print_summary('gaia-ui-tests')

        self.buildbot_status(tbpl_status, level=level)

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(PandaTest, self).query_abs_dirs()
        dirs = {}
        dirs['abs_test_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'tests')
        dirs['abs_gaiatest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'gaiatest', 'gaiatest')
        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def close_request(self):
        mph = self.query_mozpool_handler(self.mozpool_device)
        mph.close_request(self.request_url)
        self.info("Request '%s' deleted on cleanup" % self.request_url)
        self.request_url = None

    def _retry_sleep(self, sleep_time=1, max_retries=5, error_message=None, tbpl_status=None):
        for x in range(1, max_retries + 1):
            yield x
            sleep(sleep_time)
        if error_message:
            self.error(error_message)
        if tbpl_status:
            self.buildbot_status(tbpl_status)
        self.fatal('Retries limit exceeded')

    def _wait_for_request_ready(self):
        mph = self.query_mozpool_handler(self.mozpool_device)
        for retry in self._retry_sleep(sleep_time=RETRY_INTERVAL, max_retries=MAX_RETRIES,
                error_message="INFRA-ERROR: Request did not become ready in time",
                tbpl_status=TBPL_RETRY):
            response = mph.query_request_status(self.request_url)
            state = response['state']
            if state == 'ready':
                return
            self.info("Waiting for request 'ready' stage.  Current state: '%s'" % state)

if __name__ == '__main__':
    pandaTest = PandaTest()
    pandaTest.run()
