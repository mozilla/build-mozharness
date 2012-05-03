#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Generic error lists.

Error lists are used to parse output in mozharness.base.log.OutputParser.

Each line of output is matched against each substring or regular expression
in the error list.  On a match, we determine the 'level' of that line,
whether IGNORE, DEBUG, INFO, WARNING, ERROR, CRITICAL, or FATAL.

TODO: Context lines (requires work on the OutputParser side)

TODO: We could also create classes that generate these, but with the
appropriate level (please don't die on any errors; please die on any
warning; etc.) or platform or language or whatever.
"""

import re

from mozharness.base.log import WARNING, ERROR, CRITICAL, FATAL

# Exceptions
class VCSException(Exception):
    pass

# ErrorLists {{{1

BaseErrorList = [
 {'substr': r'''command not found''', 'level': ERROR},
]

# For ssh, scp, rsync over ssh
SSHErrorList = BaseErrorList + [
 {'substr': r'''Name or service not known''', 'level': ERROR},
 {'substr': r'''Could not resolve hostname''', 'level': ERROR},
 {'substr': r'''POSSIBLE BREAK-IN ATTEMPT''', 'level': WARNING},
 {'substr': r'''Network error:''', 'level': ERROR},
 {'substr': r'''Access denied''', 'level': ERROR},
 {'substr': r'''Authentication refused''', 'level': ERROR},
 {'substr': r'''Out of memory''', 'level': ERROR},
 {'substr': r'''Connection reset by peer''', 'level': WARNING},
 {'substr': r'''Host key verification failed''', 'level': ERROR},
 {'substr': r'''WARNING:''', 'level': WARNING},
 {'substr': r'''rsync error:''', 'level': ERROR},
 {'substr': r'''Broken pipe:''', 'level': ERROR},
 {'substr': r'''Permission denied:''', 'level': ERROR},
 {'substr': r'''connection unexpectedly closed''', 'level': ERROR},
 {'substr': r'''Warning: Identity file''', 'level': ERROR},
 {'substr': r'''command-line line 0: Missing argument''', 'level': ERROR},
]

HgErrorList = BaseErrorList + [
 {'regex': re.compile(r'''^abort:'''), 'level': ERROR},
 {'substr': r'''unknown exception encountered''', 'level': ERROR},
 {'substr': r'''failed to import extension''', 'level': WARNING},
]

PythonErrorList = BaseErrorList + [
 {'substr': r'''Traceback (most recent call last)''', 'level': ERROR},
 {'substr': r'''SyntaxError: ''', 'level': ERROR},
 {'substr': r'''TypeError: ''', 'level': ERROR},
 {'substr': r'''NameError: ''', 'level': ERROR},
 {'substr': r'''ZeroDivisionError: ''', 'level': ERROR},
 {'regex': re.compile(r'''raise \w*Exception: '''), 'level': CRITICAL},
 {'regex': re.compile(r'''raise \w*Error: '''), 'level': CRITICAL},
]

VirtualenvErrorList = [
 {'substr': r'''not found or a compiler error:''', 'level': ERROR},
 {'regex': re.compile('''\d+: error: '''), 'level': ERROR},
 {'regex': re.compile('''\d+: warning: '''), 'level': WARNING},
] + PythonErrorList


# We may need to have various MakefileErrorLists for differing amounts of
# warning-ignoring-ness.
MakefileErrorList = BaseErrorList + [
 {'substr': r'''No rule to make target ''', 'level': ERROR},
 {'regex': re.compile(r'''akefile.*was not found\.'''), 'level': ERROR},
 {'regex': re.compile(r'''Stop\.$'''), 'level': ERROR},
 {'regex': re.compile(r''':\d+: error:'''), 'level': ERROR},
 {'regex': re.compile(r'''make\[\d+\]: \*\*\* \[.*\] Error \d+'''), 'level': ERROR},
 {'regex': re.compile(r''':\d+: warning:'''), 'level': WARNING},
 {'substr': r'''Warning: ''', 'level': WARNING},
]

JarsignerErrorList = [{
    'substr': r'''command not found''',
    'level': FATAL
},{
    'substr': r'''jarsigner error: java.lang.RuntimeException: keystore load: Keystore was tampered with, or password was incorrect''',
    'level': FATAL,
    'explanation': r'''The store passphrase is probably incorrect!''',
},{
    'regex': re.compile(r'''jarsigner: key associated with .* not a private key'''),
    'level': FATAL,
    'explanation': r'''The key passphrase is probably incorrect!''',
},{
    'regex': re.compile(r'''jarsigner error: java.lang.RuntimeException: keystore load: .* .No such file or directory'''),
    'level': FATAL,
    'explanation': r'''The keystore doesn't exist!''',
},{
    'substr': r'''jarsigner: unable to open jar file:''',
    'level': FATAL,
    'explanation': r'''The apk is missing!''',
}]

ZipErrorList = BaseErrorList + [{
    'substr': r'''zip warning:''',
    'level': WARNING,
},{
    'substr': r'''zip error:''',
    'level': ERROR,
},{
    'substr': r'''Cannot open file: it does not appear to be a valid archive''',
    'level': ERROR,
}]

ZipalignErrorList = BaseErrorList + [{
    'regex': re.compile(r'''Unable to open .* as a zip archive'''),
    'level': ERROR,
},{
    'regex': re.compile(r'''Output file .* exists'''),
    'level': ERROR,
},{
    'substr': r'''Input and output can't be the same file''',
    'level': ERROR,
}]



# __main__ {{{1

if __name__ == '__main__':
    '''TODO: unit tests.
    '''
    pass
