#!/usr/bin/env python
"""Generic error regexes.
"""

# TODO: We could also create classes that generate these, but with the
# appropriate level (please don't die on any errors; please die on any
# warning; etc.) or platform or language or whatever.
#
# TODO: Context lines (requires work on the runCommand side)
#
# TODO:  We could have a generic shell command error list
# (e.g. File not found, permission denied) that others could be based on.

# ErrorLists {{{1

# For ssh, scp, rsync over ssh
SSHErrorList=[
 {'substr': 'Name or service not known', 'level': 'error'},
 {'substr': 'Could not resolve hostname', 'level': 'error'},
 {'substr': 'POSSIBLE BREAK-IN ATTEMPT', 'level': 'warning'},
 {'substr': 'Network error:', 'level': 'error'},
 {'substr': 'Access denied', 'level': 'error'},
 {'substr': 'Authentication refused', 'level': 'error'},
 {'substr': 'Out of memory', 'level': 'error'},
 {'substr': 'Connection reset by peer', 'level': 'warning'},
 {'substr': 'Host key verification failed', 'level': 'error'},
 {'substr': 'command not found', 'level': 'error'},
 {'substr': 'WARNING:', 'level': 'warning'},
 {'substr': 'rsync error:', 'level': 'error'},
 {'substr': 'Broken pipe:', 'level': 'error'},
 {'substr': 'connection unexpectedly closed:', 'level': 'error'},
]

HgErrorList=[
 {'regex': '^abort:', 'level': 'error'},
 {'substr': 'command not found', 'level': 'error'},
 {'substr': 'unknown exception encountered', 'level': 'error'},
]

PythonErrorList=[
 {'substr': 'Traceback (most recent call last)', 'level': 'error'},
 {'substr': 'SyntaxError: ', 'level': 'error'},
 {'substr': 'TypeError: ', 'level': 'error'},
 {'substr': 'NameError: ', 'level': 'error'},
 {'substr': 'ZeroDivisionError: ', 'level': 'error'},
 {'substr': 'command not found', 'level': 'error'},
]

# We may need to have various MakefileErrorLists for differing amounts of
# warning-ignoring-ness.
MakefileErrorList = [
 {'substr': 'No rule to make target ', 'level': 'error'},
 {'regex': 'akefile.*was not found\.', 'level': 'error'},
 {'regex': 'Stop\.$', 'level': 'error'},
 {'regex': ':\d+: error:', 'level': 'error'},
 {'regex': 'make\[\d+\]: \*\*\* \[.*\] Error \d+', 'level': 'error'},
 {'regex': ':\d+: warning:', 'level': 'warning'},
 {'substr': 'Warning: ', 'level': 'warning'},
]



# __main__ {{{1

if __name__ == '__main__':
    """TODO: unit tests.
    """
    pass
