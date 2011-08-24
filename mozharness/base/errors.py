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
'''Generic error regexes.
'''

# TODO: We could also create classes that generate these, but with the
# appropriate level (please don't die on any errors; please die on any
# warning; etc.) or platform or language or whatever.
#
# TODO: Context lines (requires work on the runCommand side)
#
# TODO:  We could have a generic shell command error list
# (e.g. File not found, permission denied) that others could be based on.

# Exceptions
class VCSException(Exception):
    pass

# ErrorLists {{{1

# For ssh, scp, rsync over ssh
SSHErrorList=[
 {'substr': r'''Name or service not known''', 'level': 'error'},
 {'substr': r'''Could not resolve hostname''', 'level': 'error'},
 {'substr': r'''POSSIBLE BREAK-IN ATTEMPT''', 'level': 'warning'},
 {'substr': r'''Network error:''', 'level': 'error'},
 {'substr': r'''Access denied''', 'level': 'error'},
 {'substr': r'''Authentication refused''', 'level': 'error'},
 {'substr': r'''Out of memory''', 'level': 'error'},
 {'substr': r'''Connection reset by peer''', 'level': 'warning'},
 {'substr': r'''Host key verification failed''', 'level': 'error'},
 {'substr': r'''command not found''', 'level': 'error'},
 {'substr': r'''WARNING:''', 'level': 'warning'},
 {'substr': r'''rsync error:''', 'level': 'error'},
 {'substr': r'''Broken pipe:''', 'level': 'error'},
 {'substr': r'''connection unexpectedly closed:''', 'level': 'error'},
]

HgErrorList=[
 {'regex': r'''^abort:''', 'level': 'error'},
 {'substr': r'''command not found''', 'level': 'error'},
 {'substr': r'''unknown exception encountered''', 'level': 'error'},
]

PythonErrorList=[
 {'substr': r'''Traceback (most recent call last)''', 'level': 'error'},
 {'substr': r'''SyntaxError: ''', 'level': 'error'},
 {'substr': r'''TypeError: ''', 'level': 'error'},
 {'substr': r'''NameError: ''', 'level': 'error'},
 {'substr': r'''ZeroDivisionError: ''', 'level': 'error'},
 {'substr': r'''command not found''', 'level': 'error'},
]

# We may need to have various MakefileErrorLists for differing amounts of
# warning-ignoring-ness.
MakefileErrorList = [
 {'substr': r'''No rule to make target ''', 'level': 'error'},
 {'regex': r'''akefile.*was not found\.''', 'level': 'error'},
 {'regex': r'''Stop\.$''', 'level': 'error'},
 {'regex': r''':\d+: error:''', 'level': 'error'},
 {'regex': r'''make\[\d+\]: \*\*\* \[.*\] Error \d+''', 'level': 'error'},
 {'regex': r''':\d+: warning:''', 'level': 'warning'},
 {'substr': r'''Warning: ''', 'level': 'warning'},
]



# __main__ {{{1

if __name__ == '__main__':
    '''TODO: unit tests.
    '''
    pass
