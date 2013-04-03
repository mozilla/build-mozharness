#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Mozilla error lists for running tests.

Error lists are used to parse output in mozharness.base.log.OutputParser.

Each line of output is matched against each substring or regular expression
in the error list.  On a match, we determine the 'level' of that line,
whether IGNORE, DEBUG, INFO, WARNING, ERROR, CRITICAL, or FATAL.

"""

import re
from mozharness.base.log import INFO, WARNING, ERROR

# ErrorLists {{{1
TinderBoxPrintRe = {
    "mochitest_summary": {
        'regex': re.compile(r'''(\d+ INFO (Passed|Failed|Todo):\ +(\d+)|\t(Passed|Failed|Todo): (\d+))'''),
        'pass_group': "Passed",
        'fail_group': "Failed",
        'known_fail_group': "Todo",
    },
    "reftest_summary": {
        'regex': re.compile(r'''REFTEST INFO \| (Successful|Unexpected|Known problems): (\d+) \('''),
        'pass_group': "Successful",
        'fail_group': "Unexpected",
        'known_fail_group': "Known problems",
    },
    "crashtest_summary": {
        'regex': re.compile(r'''REFTEST INFO \| (Successful|Unexpected|Known problems): (\d+) \('''),
        'pass_group': "Successful",
        'fail_group': "Unexpected",
        'known_fail_group': "Known problems",
    },
    "xpcshell_summary": {
        'regex': re.compile(r'''INFO \| (Passed|Failed): (\d+)'''),
        'pass_group': "Passed",
        'fail_group': "Failed",
        'known_fail_group': None,
    },
    "harness_error": {
        'full_regex': re.compile(r"(?:TEST-UNEXPECTED-FAIL|PROCESS-CRASH) \| .* \| (application crashed|missing output line for total leaks!|negative leaks caught!|\d+ bytes leaked)"),
        'minimum_regex': re.compile(r'''(TEST-UNEXPECTED|PROCESS-CRASH)''')
    },
}

TestPassed = [
    {'regex': re.compile('''(TEST-INFO|TEST-KNOWN-FAIL|TEST-PASS|INFO \| )'''), 'level': INFO},
]

LogcatErrorList = [
    {'substr': 'Fatal signal 11 (SIGSEGV)', 'level': ERROR, 'explanation': 'This usually indicates the B2G process has crashed'},
    {'substr': 'Fatal signal 7 (SIGBUS)', 'level': ERROR, 'explanation': 'This usually indicates the B2G process has crashed'},
    {'substr': '[JavaScript Error:', 'level': WARNING},
]
