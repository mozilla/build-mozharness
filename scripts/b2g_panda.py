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

from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_WARNING, TBPL_FAILURE, TBPL_RETRY, BuildbotMixin
from mozharness.base.python import VirtualenvMixin
from mozharness.base.script import BaseScript
from mozharness.mozilla.testing.testbase import TestingMixin
from mozharness.base.log import WARNING, ERROR
from mozharness.mozilla.testing.mozpool import MozpoolMixin, MozpoolConflictException

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

    mozbase_dir = os.path.join('tests', 'mozbase')
    virtualenv_modules = [
        'requests',
    ]

    def __init__(self, require_config_file=False):
        super(PandaTest, self).__init__(
            config_options=self.config_options,
            all_actions=['clobber',
                         'read-buildbot-config',
                         'create-virtualenv',
                         'request-device',
                         'run-test',
                         'close-request'],
            default_actions=['clobber',
                             'create-virtualenv',
                             'request-device',
                             'run-test',
                             'close-request'],
            require_config_file=require_config_file,
            config={'virtualenv_modules': self.virtualenv_modules,
                    'require_test_zip': True,})

        # these are necessary since self.config is read only
        self.mozpool_device = self.config.get('mozpool_device')
        if self.mozpool_device is None:
            self.fatal('--mozpool-device is required')
        self.mozpool_assignee = self.config.get('mozpool_assignee')
        if self.mozpool_assignee is None:
            self.mozpool_assignee = self.buildbot_config.get('properties')["slavename"]
        if self.mozpool_assignee is None:
            self.fatal('--mozpool-assignee is required')
        self.mozpool_b2gbase = self.config.get('mozpool_b2gbase')
        self.request_url = None

    def retry_sleep(self, sleep_time=1, max_retries=5, error_message=None, tbpl_status=None):
        for x in range(1, max_retries + 1):
            yield x
            sleep(sleep_time)
        if error_message:
            self.error(error_message)
        if tbpl_status:
            self.buildbot_status(tbpl_status)
        self.fatal('Retries limit exceeded')

    def request_device(self):
        mph = self.query_mozpool_handler()
        for retry in self.retry_sleep(sleep_time=RETRY_INTERVAL, max_retries=MAX_RETRIES,
                error_message="INFRA-ERROR: Could not request device '%s'" % self.mozpool_device,
                tbpl_status=TBPL_RETRY):
            try:
                duration = REQUEST_DURATION
                image = 'b2g'
                b2gbase = self.mozpool_b2gbase

                response = mph.request_device(self.mozpool_device, self.mozpool_assignee, image, duration, \
                               b2gbase=b2gbase, pxe_config=None)
                break
            except MozpoolConflictException:
                self.warning("Device unavailable.  Retry#%i.." % retry)

        self.request_url = response['request']['url']
        self.info("Got request, url=%s" % self.request_url)
        self.wait_for_request_ready()

    def wait_for_request_ready(self):
        mph = self.query_mozpool_handler()
        for retry in self.retry_sleep(sleep_time=RETRY_INTERVAL, max_retries=MAX_RETRIES,
                error_message="INFRA-ERROR: Request did not become ready in time",
                tbpl_status=TBPL_RETRY):
            response = mph.query_request_status(self.request_url)
            state = response['state']
            if state == 'ready':
                return
            self.info("Waiting for request 'ready' stage.  Current state: '%s'" % state)

    def run_test(self):
        """
        Run the Panda tests
        """

        '''
        level = INFO
        if code == 0:
            status = "success"
            tbpl_status = TBPL_SUCCESS
        elif code == 10:
            status = "test failures"
            tbpl_status = TBPL_WARNING
        else:
            status = "harness failures"
            level = ERROR
            tbpl_status = TBPL_FAILURE
        '''

    def close_request(self):
        mph = self.query_mozpool_handler()
        mph.close_request(self.request_url)
        print("Request '%s' deleted on cleanup" % self.request_url)
        self.request_url = None

if __name__ == '__main__':
    pandaTest = PandaTest()
    pandaTest.run()
