#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import os
import sys
from time import sleep

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.mozilla.buildbot import TBPL_RETRY, BuildbotMixin
from mozharness.base.python import VirtualenvMixin
from mozharness.base.script import BaseScript
from mozharness.mozilla.testing.testbase import TestingMixin
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
    ]

    error_list = []

    virtualenv_modules = [
        'requests',
        'mozdevice',
    ]

    def __init__(self, require_config_file=False):
        super(PandaTest, self).__init__(
            config_options=self.config_options,
            all_actions=['clobber',
                         'read-buildbot-config',
                         'create-virtualenv',
                         'download-and-extract',
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
        mph = self.query_mozpool_handler()
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
                self.warning("Device unavailable.  Retry#%i.." % retry)
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
        sys.path.append(self.query_python_site_packages_path())
        from mozdevice.devicemanagerSUT import DeviceManagerSUT
        APP_INI_LOCATION = '/system/b2g/application.ini'
        dm = None
        try:
            self.info("Connecting to: %s" % device)
            dm = DeviceManagerSUT(device)
        except:
            self.buildbot_status(TBPL_RETRY)
            self.fatal("ERROR: Unable to properly connect to SUT Port on device.")
        # No need for 300 second SUT socket timeouts here
        dm.default_timeout = 30
        if not dm.fileExists(APP_INI_LOCATION):
            self.buildbot_status(TBPL_RETRY)
            self.fatal("ERROR: expected file (%s) not found" % APP_INI_LOCATION)
        file_contents = dm.catFile(APP_INI_LOCATION)
        if file_contents is None:
            self.buildbot_status(TBPL_RETRY)
            self.fatal("ERROR: Unable to read file (%s)" % APP_INI_LOCATION)
        self.info("Read of file (%s) follows" % APP_INI_LOCATION)
        self.info("===========================")
        self.info(file_contents)

    def close_request(self):
        mph = self.query_mozpool_handler()
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
        mph = self.query_mozpool_handler()
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
