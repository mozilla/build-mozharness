#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla.
#
# The Initial Developer of the Original Code is
# the Mozilla Foundation <http://www.mozilla.org/>.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Aki Sasaki <aki@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
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

from mozharness.base.log import DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, IGNORE

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



# __main__ {{{1

if __name__ == '__main__':
    '''TODO: unit tests.
    '''
    pass
