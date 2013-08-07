#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import copy
import getpass
import os
import sys
import time

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_FAILURE, TBPL_WARNING, BuildbotMixin
from mozharness.base.log import INFO, ERROR
from mozharness.base.python import VirtualenvMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.testing.mozpool import MozpoolMixin
from mozharness.mozilla.testing.device import SUTDeviceMozdeviceMixin
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options
from mozharness.mozilla.testing.unittest import TestSummaryOutputParserHelper

class PandaTest(TestingMixin, MercurialScript, VirtualenvMixin, MozpoolMixin, BuildbotMixin, SUTDeviceMozdeviceMixin):
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
            "dest": "installer_url",
            "help": "Set b2gbase url",
        }],
        [["--test-type"], {
            "dest": "test_type",
            "default": "b2g",
            "help": "Specifies the --type parameter to pass to Marionette",
        }],
    ] + copy.deepcopy(testing_config_options)

    error_list = []
    mozpool_handler = None

    mozbase_dir = os.path.join('tests', 'mozbase')
    virtualenv_modules = [
        'mozpoolclient',
        'mozinstall',
        {
            'name': 'marionette',
            'url': os.path.join('tests', 'marionette/client'),
        },
        {
            'name': 'gaiatest',
            'url': 'gaia-ui-tests/',
        },
    ]

    repos = [{
            'repo': 'http://hg.mozilla.org/integration/gaia-ui-tests/',
            'revision': 'default',
            'dest': 'gaia-ui-tests'
            }]

    def __init__(self, require_config_file=False):
        super(PandaTest, self).__init__(
            config_options=self.config_options,
            all_actions=['clobber',
                         'read-buildbot-config',
                         'pull',
                         'download-and-extract',
                         'create-virtualenv',
                         'request-device',
                         'run-test',
                         'close-request'],
            default_actions=['clobber',
                             'pull',
                             'create-virtualenv',
                             'download-and-extract',
                             'request-device',
                             'run-test',
                             'close-request'],
            require_config_file=require_config_file,
            config={'virtualenv_modules': self.virtualenv_modules,
                    'require_test_zip': True,
                    'repos': self.repos})

        self.mozpool_assignee = self.config.get('mozpool_assignee', getpass.getuser())
        self.request_url = None
        self.mozpool_device = self.config.get("mozpool_device")
        self.installer_url = self.config.get("installer_url")
        self.test_url = self.config.get("test_url")
        self.gaia_ui_tests_commit = 'unknown'

    def postflight_read_buildbot_config(self):
        super(PandaTest, self).postflight_read_buildbot_config()
        self.mozpool_device = self.config.get('mozpool_device', \
                self.buildbot_config.get('properties')["slavename"])

    def request_device(self):
        self.retrieve_b2g_device(b2gbase=self.installer_url)

    def _sut_prep_steps(self):
        APP_INI_LOCATION = '/system/b2g/application.ini'
        try:
            file_contents = self.query_file(APP_INI_LOCATION)
            self.info("Read of file (%s) follows" % APP_INI_LOCATION)
            self.info("===========================")
            self.info(file_contents)
        except Exception, e:
            self._retry_job_and_close_request("We failed to output %s" % APP_INI_LOCATION, e)

        device_time = self.set_device_epoch_time()
        self.info("Current time on device: %s - %s" % \
            (device_time, time.strftime("%x %H:%M:%S", time.gmtime(float(device_time)))))

    def pull(self, **kwargs):
        repos = super(PandaTest, self).pull(**kwargs)
        self.gaia_ui_tests_commit = repos['gaia-ui-tests']['revision']

    def run_test(self):
        self._sut_prep_steps()

        level = INFO
        env = self.query_env()
        env["DM_TRANS"] = "sut"
        env["TEST_DEVICE"] = self.mozpool_device
        env["GAIATEST_ACKNOWLEDGED_RISKS"] = 1
        env["GAIATEST_SKIP_WARNING"] = 1
        self.info("Running tests...")
        dirs = self.query_abs_dirs()
        cmd = [self.query_python_path('gaiatest'),
               '--address', '%s:2828' % self.mozpool_device,
               '--type', self.config['test_type'],
               os.path.join(dirs['abs_gaiatest_dir'], 'tests', 'manifest.ini')]
        test_summary_parser = TestSummaryOutputParserHelper(config=self.config, log_obj=self.log_obj)

        code = self.run_command(cmd, env=env, output_parser=test_summary_parser)
        if code == 0 and test_summary_parser.passed > 0 and test_summary_parser.failed == 0:
            tbpl_status = TBPL_SUCCESS
        elif code == 10 and test_summary_parser.failed > 0:
            tbpl_status = TBPL_WARNING
        else:
            level = ERROR
            tbpl_status = TBPL_FAILURE

        if tbpl_status != TBPL_SUCCESS:
            self.info("Output logcat...")
            try:
                lines = self.get_logcat()
                for l in lines:
                    self.info(l)
            except Exception, e:
                self.warning("We failed to run logcat: str(%s)" % str(e))

        test_summary_parser.print_summary('gaia-ui-tests')
        self.info("TinderboxPrint: gaia-ui-tests_revlink: %s/rev/%s" %
                  (self.config.get('repos')[0]['repo'], self.gaia_ui_tests_commit))

        self.buildbot_status(tbpl_status, level=level)

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(PandaTest, self).query_abs_dirs()
        dirs = {}
        dirs['abs_test_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'tests')
        dirs['abs_gaiatest_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'gaia-ui-tests', 'gaiatest')
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

if __name__ == '__main__':
    pandaTest = PandaTest()
    pandaTest.run_and_exit()
