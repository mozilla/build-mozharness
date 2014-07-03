# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
import json

from mozharness.base import log
from mozharness.base.log import OutputParser, WARNING, INFO, CRITICAL
from mozharness.mozilla.buildbot import TBPL_WARNING, TBPL_FAILURE
from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_WORST_LEVEL_TUPLE

#TODO: reuse the formatter in mozlog

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
            return "TEST-END TEST-UNEXPECTED-%s | %s | expected %s | %s | took %ims" % (
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

        return self.tbpl_status, self.worst_log_level

    def update_levels(self, tbpl_level, log_level):
        self.worst_log_level = self.worst_level(log_level, self.worst_log_level)
        self.tbpl_status = self.worst_level(tbpl_level, self.tbpl_status,
                                            levels=TBPL_WORST_LEVEL_TUPLE)
