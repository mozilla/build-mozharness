#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import copy
import getpass
import os
import re
import sys
import time
import socket

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.mozilla.buildbot import TBPL_SUCCESS, BuildbotMixin
from mozharness.base.errors import BaseErrorList
from mozharness.base.log import INFO, ERROR, FATAL
from mozharness.base.python import VirtualenvMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.testing.mozpool import MozpoolMixin
from mozharness.mozilla.testing.device import SUTDeviceMozdeviceMixin
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options
from mozharness.mozilla.testing.unittest import DesktopUnittestOutputParser

SUITE_CATEGORIES = ['mochitest', 'reftest', 'crashtest', 'jsreftest', 'robocop']


class PandaTest(TestingMixin, MercurialScript, VirtualenvMixin, MozpoolMixin, BuildbotMixin, SUTDeviceMozdeviceMixin):
    test_suites =  SUITE_CATEGORIES
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
        [["--total-chunks"], {
             "action": "store",
             "dest": "total_chunks",
             "help": "Number of total chunks",
        }],
        [["--this-chunk"], {
             "action": "store",
             "dest": "this_chunk",
             "help": "Number of this chunk",
        }],
        [["--extra-args"], {
             "action": "store",
             "dest": "extra_args",
             "help": "Extra arguments",
        }],
        [['--mochitest-suite', ], {
             "action": "extend",
             "dest": "specified_mochitest_suites",
             "type": "string",
             "help": "Specify which mochi suite to run. "
                    "Suites are defined in the config file.\n"
                    "Examples: 'all', 'plain1', 'plain5', 'chrome', or 'a11y'"}
         ],
         [['--reftest-suite', ], {
             "action": "extend",
             "dest": "specified_reftest_suites",
             "type": "string",
             "help": "Specify which reftest suite to run. "
                     "Suites are defined in the config file.\n"
                     "Examples: 'all', 'crashplan', or 'jsreftest'"}
         ],
         [['--crashtest-suite', ], {
             "action": "extend",
             "dest": "specified_crashtest_suites",
             "type": "string",
             "help": "Specify which crashtest suite to run. "
                     "Suites are defined in the config file\n."
                     "Examples: 'crashtest'"}
         ],
         [['--jsreftest-suite', ], {
             "action": "extend",
             "dest": "specified_jsreftest_suites",
             "type": "string",
             "help": "Specify which jsreftest suite to run. "
                     "Suites are defined in the config file\n."
                     "Examples: 'jsreftest'"}
         ],
         [['--robocop-suite', ], {
             "action": "extend",
             "dest": "specified_robocop_suites",
             "type": "string",
             "help": "Specify which robocop suite to run. "
                     "Suites are defined in the config file\n."
                     "Examples: 'robocop'"}
         ],
         [['--run-all-suites', ], {
            "action": "store_true",
            "dest": "run_all_suites",
            "default": False,
            "help": "This will run all suites that are specified "
                    "in the config file. You do not need to specify "
                    "any other suites.\nBeware, this may take a while ;)"}
         ],
    ] + copy.deepcopy(testing_config_options)

    error_list = []
    mozpool_handler = None

    virtualenv_modules = [
        'mozpoolclient',
        'mozcrash'
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
                             'read-buildbot-config',
                             'create-virtualenv',
                             'download-and-extract',
                             'request-device',
                             'run-test',
                             'close-request'],
            require_config_file=require_config_file,
            config={'virtualenv_modules': self.virtualenv_modules})

        self.mozpool_assignee = self.config.get('mozpool_assignee', getpass.getuser())
        self.request_url = None
        self.test_url = self.config.get("test_url")
        self.mozpool_device = self.config.get("mozpool_device")
        self.symbols_url = self.config.get('symbols_url')

    def postflight_read_buildbot_config(self):
        super(PandaTest, self).postflight_read_buildbot_config()
        self.mozpool_device = self.config.get('mozpool_device', \
                self.buildbot_config.get('properties')["slavename"])

    def request_device(self):
        self.retrieve_android_device(b2gbase="")
        sys.path.append(self.config.get("verify_path"))
        try:
            from verify import verifyDevice
            #call verifyscript to get location of it on the filesystem
            if verifyDevice(self.mozpool_device, checksut=True, doCheckStalled=False, watcherINI=True) == False:
                self.error("failed to run verify on %s" % (self.mozpool_device))
            else:
                self.info("Successfully verified the device")
        except ImportError, e:
            self.fatal("Can't import DeviceManagerSUT! %s\nDid you check out talos?" % str(e))

    def _sut_prep_steps(self):
        device_time = self.set_device_epoch_time()
        self.info("Current time on device: %s - %s" % \
            (device_time, time.strftime("%x %H:%M:%S", time.gmtime(float(device_time)))))

    def _run_category_suites(self, suite_category, preflight_run_method=None):
        """run suite(s) to a specific category"""

        env = self.query_env(partial_env={'DM_TRANS': "sut", 'TEST_DEVICE': self.mozpool_device})
        self.info("Running tests...")

        suites = self._query_specified_suites(suite_category)
        level = INFO

        if preflight_run_method:
            preflight_run_method(suites)
        if suites:
            self.info('#### Running %s suites' % suite_category)
            for suite in suites:
                self._download_unzip_hostutils()
                abs_base_cmd = self._query_abs_base_cmd(suite_category)
                if 'robocop' in suite:
                    self._download_robocop_apk()
                self._install_app()
                cmd = abs_base_cmd[:]
                replace_dict = {}
                for arg in suites[suite]:
                    cmd.append(arg % replace_dict)              
                if 'mochitest-gl' in suite:
                     cmd.remove("--run-only-tests=android.json")                   
                tbpl_status, log_level = None, None
                error_list = BaseErrorList + [{
                    'regex': re.compile(r"(?:TEST-UNEXPECTED-FAIL|PROCESS-CRASH) \| .* \| (application crashed|missing output line for total leaks!|negative leaks caught!|\d+ bytes leaked)"),
                    'level': ERROR,
                }]
                test_summary_parser = DesktopUnittestOutputParser(suite_category,
                                                     config=self.config,
                                                     error_list=error_list,
                                                     log_obj=self.log_obj)

                dirs = self.query_abs_dirs()
                return_code = self.run_command(cmd, dirs['abs_test_install_dir'], env=env, output_parser=test_summary_parser)

                tbpl_status, log_level = test_summary_parser.evaluate_parser(return_code)

                if tbpl_status != TBPL_SUCCESS:
                    self.info("Output logcat...")
                    try:
                        lines = self.get_logcat()
                        self.info("*** STARTING LOGCAT ***")
                        for l in lines:
                            self.info(l)
                        self.info("*** END LOGCAT ***")
                    except Exception, e:
                        self.warning("We failed to run logcat: str(%s)" % str(e))

                test_summary_parser.append_tinderboxprint_line(suite)
                self.buildbot_status(tbpl_status, level=level)

                self.log("The %s suite: %s ran with return status: %s" %
                            (suite_category, suite, tbpl_status), level=log_level)

    def _query_specified_suites(self, category):
        # logic goes: if at least one '--{category}-suite' was given,
        # then run only that(those) given suite(s). Elif no suites were
        # specified and the --run-all-suites flag was given,
        # run all {category} suites. Anything else, run no suites.
        c = self.config
        all_suites = c.get('all_%s_suites' % (category))
        specified_suites = c.get('specified_%s_suites' % (category))  # list

        suites = None

        if specified_suites:
            if 'all' in specified_suites:
                # useful if you want a quick way of saying run all suites
                # of a specific category.
                suites = all_suites
            else:
                # suites gets a dict of everything from all_suites where a key
                # is also in specified_suites
                suites = dict((key, all_suites.get(key)) for key in
                              specified_suites if key in all_suites.keys())
        else:
            if c.get('run_all_suites'):  # needed if you dont specify any suites
                suites = all_suites

        return suites


    def run_test(self):
       # do we need to set the device time?
       # command doesn't work anyways
       # self._sut_prep_steps()

        env = self.query_env()
        env["DM_TRANS"] = "sut"
        env["TEST_DEVICE"] = self.mozpool_device
        self.info("Running tests...")

        for category in SUITE_CATEGORIES:
            self._run_category_suites(category)

    def _download_unzip_hostutils(self):
          c = self.config
          dirs = self.query_abs_dirs()
          self.host_utils_url = c['hostutils_url']
          #create the hostutils dir, get the zip and extract it
          self.mkdir_p(dirs['abs_hostutils_dir'])
          self._download_unzip(self.host_utils_url,dirs['abs_hostutils_dir'])

    def _install_app(self):
          c = self.config
          base_work_dir = c['base_work_dir']
          cmd = ['python',self.config.get("install_app_path"), self.device_ip, 'build/'+ str(self.filename_apk), self.app_name]
          self.run_command(cmd, base_work_dir, halt_on_failure=True)

    def _download_robocop_apk(self):
         dirs = self.query_abs_dirs()
         self.apk_url = self.installer_url[:self.installer_url.rfind('/')]
         robocop_url = self.apk_url + '/robocop.apk'
         self.info("Downloading robocop...")   
         self.download_file(robocop_url, 'robocop.apk', dirs['abs_work_dir'], error_level=FATAL)

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(PandaTest, self).query_abs_dirs()
        dirs = {}
        dirs['abs_test_install_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'tests')
        dirs['abs_mochitest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'mochitest')
        dirs['abs_reftest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'reftest')
        dirs['abs_crashtest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'reftest')
        dirs['abs_jsreftest_dir'] = os.path.join(
            dirs['abs_test_install_dir'], 'reftest')
        dirs['abs_xre_dir'] = os.path.join(
             abs_dirs['abs_work_dir'], 'xre')
        dirs['abs_utility_path'] = os.path.join(
            abs_dirs['abs_work_dir'],'bin')
        dirs['abs_certificate_path'] = os.path.join(
            abs_dirs['abs_work_dir'], 'certs')
        dirs['abs_hostutils_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'hostutils')
        dirs['abs_robocop_dir'] = os.path.join(
             dirs['abs_test_install_dir'], 'mochitest')
        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def _query_symbols_url(self):
        """query the full symbols URL based upon binary URL"""
        # may break with name convention changes but is one less 'input' for script
        if self.symbols_url:
            return self.symbols_url

    def _query_abs_base_cmd(self, suite_category):
        #check for apk first with if ?
        c = self.config
        dirs = self.query_abs_dirs()
        options = []
        run_file = c['run_file_names'][suite_category]
        base_cmd = ['python']
        base_cmd.append(os.path.join((dirs["abs_%s_dir" % suite_category]), run_file))
        self.device_ip = socket.gethostbyname(self.mozpool_device)
        #applies to mochitest, reftest, jsreftest
        # TestingMixin._download_and_extract_symbols() will set
        # self.symbols_path when downloading/extracting.
        hostnumber = int(self.mozpool_device.split('-')[1])
        http_port =  '30%03i' % hostnumber
        ssl_port =  '31%03i' %  hostnumber
        #get filename from installer_url
        self.filename_apk = self.installer_url.split('/')[-1]
        #find appname from package-name.txt - assumes download-and-extract has completed successfully
        apk_dir = self.abs_dirs['abs_work_dir']
        self.apk_path = os.path.join(apk_dir, self.filename_apk)
        unzip = self.query_exe("unzip")
        package_path  = os.path.join(apk_dir,'package-name.txt')
        unzip_cmd = [unzip, '-q', '-o',  self.apk_path]
        self.run_command(unzip_cmd, cwd=apk_dir, halt_on_failure=True)
        self.app_name = str(self.read_from_file(package_path,verbose=True)).rstrip()

        str_format_values = {
                'device_ip': self.device_ip,
                'hostname': self.mozpool_device,
                'symbols_path': self._query_symbols_url(),
                'http_port': http_port,
                'ssl_port':  ssl_port,
                'app_name':  self.app_name
            }
        if self.config['%s_options' % suite_category]:
            for option in self.config['%s_options' % suite_category]:
                options.append(option % str_format_values)
            abs_base_cmd = base_cmd + options
            return abs_base_cmd
        else:
            self.warning("Suite options for %s could not be determined."
                         "\nIf you meant to have options for this suite, "
                         "please make sure they are specified in your "
                         "config under %s_options" %
                          (suite_category, suite_category))

    ###### helper methods
    def _pre_config_lock(self, rw_config):
        c = self.config
        if not c.get('run_all_suites') :
            return  # configs are valid
        for category in SUITE_CATEGORIES:
            specific_suites = c.get('specified_%s_suites' % (category))
            if specific_suites:
                if specific_suites != 'all':
                    self.fatal("Config options are not valid. Please ensure"
                               " that if the '--run-all-suites' flag was enabled,"
                               " then do not specify to run only specific suites "
                               "like:\n '--mochitest-suite browser-chrome'")

    def close_request(self):
        mph = self.query_mozpool_handler(self.mozpool_device)
        mph.close_request(self.request_url)
        self.info("Request '%s' deleted on cleanup" % self.request_url)
        self.request_url = None

    def _build_arg(self, option, value):
        """
        Build a command line argument
        """
        if not value:
            return []
        return [str(option), str(value)]

if __name__ == '__main__':
    pandaTest = PandaTest()
    pandaTest.run()
