#!/usr/bin/env python
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
