# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
import json

from mozharness.base import log
from mozharness.base.log import OutputParser, WARNING, INFO
from mozharness.mozilla.buildbot import TBPL_WARNING, TBPL_FAILURE
from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_WORST_LEVEL_TUPLE


class StructuredOutputParser(OutputParser):
    # The script class using this must inherit the MozbaseMixin to ensure
    # that mozlog is available.
    def __init__(self, **kwargs):
        """Object that tracks the overall status of the test run"""
        super(StructuredOutputParser, self).__init__(**kwargs)
        self.unexpected_count = 0
        self.formatter = self._get_formatter()

        self.worst_log_level = INFO
        self.tbpl_status = TBPL_SUCCESS

    def _get_formatter(self):
        from mozlog.structured.formatters import TbplFormatter
        return TbplFormatter()

    def parse_single_line(self, line):
        """
        Parse a line of log output from the child process and
        use this to update the overall status of the run. Then re-emit the
        logged line in human-readable format for the tbpl logs.

        The raw logs are uploaded seperately.
        """
        level = INFO
        tbpl_level = TBPL_SUCCESS

        try:
            data = json.loads(line)
        except ValueError:
            self.critical("Failed to parse line '%s' as json" % line)
            self.update_levels(TBPL_FAILURE, log.CRITICAL)
            return

        if "action" not in data:
            self.critical("Parsed JSON was not a valid structured log message: %s" % line)
            self.update_levels(TBPL_FAILURE, log.CRITICAL)
            return

        action = data["action"]
        if action == "log":
            level = getattr(log, data["level"])
        elif action in ["test_end", "test_status"] and "expected" in data:
            self.unexpected_count += 1
            level = WARNING
            tbpl_level = TBPL_WARNING
        self.log(self.formatter(data), level=level)
        self.update_levels(tbpl_level, level)

    def evaluate_parser(self, return_code):
        if self.unexpected_count > 0:
            self.update_levels(TBPL_WARNING, WARNING)

        return self.tbpl_status, self.worst_log_level

    def update_levels(self, tbpl_level, log_level):
        self.worst_log_level = self.worst_level(log_level, self.worst_log_level)
        self.tbpl_status = self.worst_level(tbpl_level, self.tbpl_status,
                                            levels=TBPL_WORST_LEVEL_TUPLE)
