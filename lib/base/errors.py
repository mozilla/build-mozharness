#!/usr/bin/env python
"""Generic error regexes.

We could also create classes that generate these, but with the appropriate
level (please don't die on any errors; please die on any warning; etc.)
"""

# ErrorRegexes {{{1
""" TODO: more of these.

We could have a generic shell command regex list (e.g. File not found,
permission denied) that others could copy (or [:] as it were)

"""

# For ssh, scp, rsync over ssh
SSHErrorRegexList=[
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

HgErrorRegexList=[
 {'regex': '^abort:', 'level': 'error'},
 {'substr': 'command not found', 'level': 'error'},
 {'substr': 'unknown exception encountered', 'level': 'error'},
]

PythonErrorRegexList=[
 {'substr': 'Traceback (most recent call last)', 'level': 'error'},
 {'substr': 'SyntaxError: ', 'level': 'error'},
 {'substr': 'TypeError: ', 'level': 'error'},
 {'substr': 'NameError: ', 'level': 'error'},
 {'substr': 'ZeroDivisionError: ', 'level': 'error'},
 {'substr': 'command not found', 'level': 'error'},
]

# TODO I haven't scratched the surface here.
# TODO populate from
#  http://www.gnu.org/software/automake/manual/make/Error-Messages.html
# This will probably be more regexes than substrs.
MakefileErrorRegexList = [
 {'substr': 'make: *** No rule to make target ', 'level': 'error'},
 {'substr': 'missing separator.  Stop.', 'level': 'error'},
]



# __main__ {{{1

if __name__ == '__main__':
    """TODO: unit tests.
    """
    pass
