#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import os

from mozharness.mozilla.testing.errors import TinderBoxPrintRe
from mozharness.base.log import OutputParser, WARNING, INFO
from mozharness.mozilla.buildbot import TBPL_WARNING, TBPL_FAILURE
from mozharness.mozilla.buildbot import TBPL_SUCCESS, TBPL_STATUS_DICT

SUITE_CATEGORIES = ['mochitest', 'reftest', 'xpcshell']


class DesktopUnittestOutputParser(OutputParser):
    """
    A class that extends OutputParser such that it can parse the number of
    passed/failed/todo tests from the output.
    """

    def __init__(self, suite_category, **kwargs):
        # worst_log_level defined already in DesktopUnittestOutputParser
        # but is here to make pylint happy
        self.worst_log_level = INFO
        super(DesktopUnittestOutputParser, self).__init__(**kwargs)
        self.summary_suite_re = TinderBoxPrintRe.get('%s_summary' % suite_category, {})
        self.harness_error_re = TinderBoxPrintRe['harness_error']['minimum_regex']
        self.full_harness_error_re = TinderBoxPrintRe['harness_error']['full_regex']
        self.fail_count = -1
        self.pass_count = -1
        # known_fail_count does not exist for some suites
        self.known_fail_count = self.summary_suite_re.get('known_fail_group') and -1
        self.crashed, self.leaked = False, False
        self.tbpl_status = TBPL_SUCCESS

    def parse_single_line(self, line):
        if self.summary_suite_re:
            summary_m = self.summary_suite_re['regex'].match(line)  # pass/fail/todo
            if summary_m:
                message = ' %s' % line
                log_level = INFO
                # remove all the none values in groups() so this will work
                # with all suites including mochitest browser-chrome
                summary_match_list = [group for group in summary_m.groups()
                                      if group is not None]
                r = summary_match_list[0]
                if self.summary_suite_re['pass_group'] in r:
                    self.pass_count = int(summary_match_list[-1])
                elif self.summary_suite_re['fail_group'] in r:
                    self.fail_count = int(summary_match_list[-1])
                    if self.fail_count > 0:
                        message += '\n One or more unittests failed.'
                        log_level = WARNING
                # If self.summary_suite_re['known_fail_group'] == None,
                # then r should not match it, # so this test is fine as is.
                elif self.summary_suite_re['known_fail_group'] in r:
                    self.known_fail_count = int(summary_match_list[-1])
                self.log(message, log_level)
                return  # skip harness check and base parse_single_line
        harness_match = self.harness_error_re.match(line)
        if harness_match:
            self.warning(' %s\n This is a harness error.' % line)
            self.worst_log_level = self.worst_level(WARNING, self.worst_log_level)
            self.tbpl_status = self.worst_level(TBPL_WARNING, self.tbpl_status,
                                                levels=TBPL_STATUS_DICT.keys())
            full_harness_match = self.full_harness_error_re.match(line)
            if full_harness_match:
                r = full_harness_match.group(1)
                if r == "Browser crashed (minidump found)":
                    self.crashed = True
                elif r == "missing output line for total leaks!":
                    self.leaked = None
                else:
                    self.leaked = True
            return  # skip base parse_single_line
        super(DesktopUnittestOutputParser, self).parse_single_line(line)

    def evaluate_parser(self, return_code):
        if self.num_errors:  # mozharness ran into a script error
            self.tbpl_status = TBPL_FAILURE

        # I have to put this outside of parse_single_line because this checks not
        # only if fail_count was more then 0 but also if fail_count is still -1
        # (no fail summary line was found)
        if self.fail_count != 0:
            self.worst_log_level = self.worst_level(WARNING, self.worst_log_level)
            self.tbpl_status = self.worst_level(TBPL_WARNING, self.tbpl_status,
                                                levels=TBPL_STATUS_DICT.keys())
        # we can trust in parser.worst_log_level in either case
        return (self.tbpl_status, self.worst_log_level)

    def append_tinderboxprint_line(self, suite_name):
        # We are duplicating a condition (fail_count) from evaluate_parser and
        # parse parse_single_line but at little cost since we are not parsing
        # the log more then once.  I figured this method should stay isolated as
        # it is only here for tbpl highlighted summaries and is not part of
        # buildbot evaluation or result status IIUC.
        emphasize_fail_text = '<em class="testfail">%s</em>'

        if self.pass_count < 0 or self.fail_count < 0 or \
                (self.known_fail_count is not None and self.known_fail_count < 0):
            summary = emphasize_fail_text % 'T-FAIL'
        elif self.pass_count == 0 and self.fail_count == 0 and \
                (self.known_fail_count == 0 or self.known_fail_count is None):
            summary = emphasize_fail_text % 'T-FAIL'
        else:
            str_fail_count = str(self.fail_count)
            if self.fail_count > 0:
                str_fail_count = emphasize_fail_text % str_fail_count
            summary = "%d/%s" % (self.pass_count, str_fail_count)
            if self.known_fail_count is not None:
                summary += "/%d" % self.known_fail_count
        # Format the crash status.
        if self.crashed:
            summary += "&nbsp;%s" % emphasize_fail_text % "CRASH"
        # Format the leak status.
        if self.leaked is not False:
            summary += "&nbsp;%s" % emphasize_fail_text % (
                (self.leaked and "LEAK") or "L-FAIL")
        # Return the summary.
        self.info("TinderboxPrint: %s<br/>%s\n" % (suite_name, summary))

class EmulatorMixin(object):
    """ Currently dependent on both TooltoolMixin and TestingMixin)"""
    def install_emulator(self):
        dirs = self.query_abs_dirs()
        self.mkdir_p(dirs['abs_emulator_dir'])
        if self.config.get('emulator_url'):
            self._download_unzip(self.config['emulator_url'], dirs['abs_emulator_dir'])
        elif self.config.get('emulator_manifest'):
            manifest_path = self.create_tooltool_manifest(self.config['emulator_manifest'])
            if self.tooltool_fetch(manifest_path, output_dir=dirs['abs_work_dir']):
                self.fatal("Unable to download emulator via tooltool!")
            unzip = self.query_exe("unzip")
            unzip_cmd = [unzip, '-q', os.path.join(dirs['abs_work_dir'], "emulator.zip")]
            self.run_command(unzip_cmd, cwd=dirs['abs_emulator_dir'], halt_on_failure=True)
        else:
            self.fatal("Can't get emulator; set emulator_url or emulator_manifest in the config!")
