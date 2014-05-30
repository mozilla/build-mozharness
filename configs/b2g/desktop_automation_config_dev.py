# This config contains dev values that will replace
# the values specified in the production config
# if specified like this (order matters):
# --cfg b2g/desktop_automation_config.py
# --cfg b2g/desktop_automation_config_dev.py
import os

config = {
    "exes": {
    },

    "find_links": [
        "http://pypi.pub.build.mozilla.org/pub",
    ],

    "default_actions": [
        'clobber',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-tests',
    ],
}
