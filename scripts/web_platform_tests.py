#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
import os
import sys
import copy
import json

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.script import PreScriptAction
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.blob_upload import BlobUploadMixin, blobupload_config_options
from mozharness.mozilla.testing.testbase import TestingMixin, testing_config_options

from mozharness.base import log
from mozharness.base.log import OutputParser, WARNING, INFO, CRITICAL
from mozharness.mozilla.buildbot import TBPL_WARNING, TBPL_FAILURE
from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_WORST_LEVEL_TUPLE


class WebPlatformTest(TestingMixin, MercurialScript, BlobUploadMixin):
    config_options = copy.deepcopy(testing_config_options) + \
                     copy.deepcopy(blobupload_config_options)

    def __init__(self, require_config_file=True):
        super(WebPlatformTest, self).__init__(
            config_options=self.config_options,
            all_actions=[
                'clobber',
                'read-buildbot-config',
                'download-and-extract',
                'create-virtualenv',
                'pull',
                'install',
                'run-tests',
            ],
            require_config_file=require_config_file,
            config={'require_test_zip': True})

        # Surely this should be in the superclass
        c = self.config
        self.installer_url = c.get('installer_url')
        self.test_url = c.get('test_url')
        self.installer_path = c.get('installer_path')
        self.binary_path = c.get('binary_path')
        self.abs_app_dir = None

    def query_abs_app_dir(self):
        """We can't set this in advance, because OSX install directories
        change depending on branding and opt/debug.
        """
        if self.abs_app_dir:
            return self.abs_app_dir
        if not self.binary_path:
            self.fatal("Can't determine abs_app_dir (binary_path not set!)")
        self.abs_app_dir = os.path.dirname(self.binary_path)
        return self.abs_app_dir

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(WebPlatformTest, self).query_abs_dirs()

        dirs = {}
        dirs['abs_app_install_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'application')
        dirs['abs_test_install_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'tests')
        dirs["abs_wpttest_dir"] = os.path.join(dirs['abs_test_install_dir'], "web-platform-tests")
        dirs['abs_blob_upload_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'blobber_upload_dir')

        abs_dirs.update(dirs)
        self.abs_dirs = abs_dirs

        return self.abs_dirs

    @PreScriptAction('create-virtualenv')
    def _pre_create_virtualenv(self, action):
        dirs = self.query_abs_dirs()

        requirements = os.path.join(dirs['abs_test_install_dir'],
                                    'config',
                                    'marionette_requirements.txt')
        if os.path.isfile(requirements):
            self.register_virtualenv_module(requirements=[requirements],
                                            two_pass=True)
            return

        # XXX Bug 879765: Dependent modules need to be listed before parent
        # modules, otherwise they will get installed from the pypi server.
        # XXX Bug 908356: This block can be removed as soon as the
        # in-tree requirements files propagate to all active trees.
        mozbase_dir = os.path.join('tests', 'mozbase')
        self.register_virtualenv_module('manifestparser',
                                        url=os.path.join(mozbase_dir, 'manifestdestiny'))

        for m in ('mozfile', 'mozlog', 'mozinfo', 'moznetwork', 'mozhttpd',
                  'mozcrash', 'mozinstall', 'mozdevice', 'mozprofile', 'mozprocess',
                  'mozrunner'):
            self.register_virtualenv_module(m, url=os.path.join(mozbase_dir,
                                                                m))

            self.register_virtualenv_module('marionette', os.path.join('tests',
                                                                       'marionette'))

    def _query_cmd(self):
        if not self.binary_path:
            self.fatal("Binary path could not be determined")
            #And exit

        c = self.config
        dirs = self.query_abs_dirs()
        abs_app_dir = self.query_abs_app_dir()
        run_file_name = "runtests.py"

        base_cmd = [self.query_python_path('python'), '-u']
        base_cmd.append(os.path.join(dirs["abs_wpttest_dir"], run_file_name))

        base_cmd += ["--log-stdout",
                     "-o=%s" % os.path.join(dirs["abs_blob_upload_dir"],
                                            "wpt_structured_full.log")]

        pos_args = [self.binary_path,
                    os.path.join(dirs["abs_wpttest_dir"], "tests")]

        options = c["options"]

        str_format_values = {
            'binary_path': self.binary_path,
            'test_path': dirs["abs_wpttest_dir"],
            'abs_app_dir': abs_app_dir
            }

        options = [item % str_format_values for item in options]

        return base_cmd + pos_args + options

    def run_tests(self):
        dirs = self.query_abs_dirs()
        cmd = self._query_cmd()

        parser = StructuredOutputParser(config=self.config,
                                        log_obj=self.log_obj)

        env = {}
        env = self.query_env(partial_env=env, log_level=INFO)
        return_code = self.run_command(cmd,
                                       cwd=dirs['abs_work_dir'],
                                       output_timeout=1000,
                                       output_parser=parser,
                                       env=env)

        tbpl_status, log_level = parser.evaluate_parser(return_code)

        self.buildbot_status(tbpl_status, level=log_level)


class StructuredFormatter(object):
    def __init__(self):
        self.suite_start_time = None
        self.test_start_times = {}

    def format(self, data):
        return getattr(self, "format_%s" % data["action"])(data)

    def format_log(self, data):
        return str(data["message"])

    def format_process_output(self, data):
        return "PROCESS | %(process)s | %(data)s" % data

    def format_suite_start(self, data):
        self.suite_start_time = data["time"]
        return "SUITE-START | Running %i tests" % len(data["tests"])

    def format_test_start(self, data):
        self.test_start_times[self.test_id(data["test"])] = data["time"]
        return "TEST-START | %s" % self.id_str(data["test"])

    def format_test_status(self, data):
        if "expected" in data:
            return "TEST-UNEXPECTED-%s | %s | %s | expected %s | %s" % (
                data["status"], self.id_str(data["test"]), data["subtest"], data["expected"],
                data.get("message", ""))
        else:
            return "TEST-%s | %s | %s | %s" % (
                data["status"], self.id_str(data["test"]), data["subtest"], data.get("message", ""))

    def format_test_end(self, data):
        start_time = self.test_start_times.pop(self.test_id(data["test"]))
        time = data["time"] - start_time

        if "expected" in data:
            return "TEST-END UNEXPECTED-%s | %s | expected %s | %s | took %ims" % (
                data["status"], self.id_str(data["test"]), data["expected"],
                data.get("message", ""), time)
        else:
            return "TEST-END %s | %s | took %ims" % (
                data["status"], self.id_str(data["test"]), time)

    def format_suite_end(self, data):
        start_time = self.suite_start_time
        time = int((data["time"] - start_time) / 1000)

        return "SUITE-END | took %is" % time

    def test_id(self, test_id):
        if isinstance(test_id, (str, unicode)):
            return test_id
        else:
            return tuple(test_id)

    def id_str(self, test_id):
        if isinstance(test_id, (str, unicode)):
            return test_id
        else:
            return " ".join(test_id)


class StructuredOutputParser(OutputParser):
    formatter_cls = StructuredFormatter

    def __init__(self, **kwargs):
        """Object that tracks the overall status of the test run"""
        super(StructuredOutputParser, self).__init__(**kwargs)
        self.unexpected_count = 0
        self.parsing_failed = False
        self.formatter = self.formatter_cls()

        self.worst_log_level = INFO
        self.tbpl_status = TBPL_SUCCESS

    def parse_single_line(self, line):
        """
        Parse a line of log output from the child process and
        use this to update the overall status of the run. Then re-emit the
        logged line in humand-readable format for the tbpl logs.

        The raw logs are uploaded seperately.
        """
        level = INFO
        tbpl_level = TBPL_SUCCESS

        try:
            data = json.loads(line)
        except ValueError:
            self.critical("Failed to parse line '%s' as json" % line)
            self.parsing_failed = True
            return

        if "action" not in data:
            self.error(line)
            return

        action = data["action"]
        if action == "log":
            level = getattr(log, data["level"])
        elif action in ["test_end", "test_status"] and "expected" in data:
            self.unexpected_count += 1
            level = WARNING
            tbpl_level = TBPL_WARNING
        self.log(self.formatter.format(data), level=level)
        self.update_levels(tbpl_level, level)

    def evaluate_parser(self, return_code):
        if self.unexpected_count > 0:
            self.update_levels(TBPL_WARNING, WARNING)

        if self.parsing_failed:
            self.update_levels(TBPL_FAILURE, CRITICAL)

        return self.tbpl_status, self.worst_log_level

    def update_levels(self, tbpl_level, log_level):
        self.worst_log_level = self.worst_level(log_level, self.worst_log_level)
        self.tbpl_status = self.worst_level(tbpl_level, self.tbpl_status,
                                            levels=TBPL_WORST_LEVEL_TUPLE)


# main {{{1
if __name__ == '__main__':
    web_platform_tests = WebPlatformTest()
    web_platform_tests.run_and_exit()
