# This config contains dev values that will replace
# the values specified in the production config
# if specified like this (order matters):
# --cfg android/androidarm.py
# --cfg android/androidarm_dev.py
import os
config = {
    "tooltool_url": "http://tooltool.pvt.build.mozilla.org/build/sha512",
    "exes": {},
    ".avds_dir": os.path.join(os.getenv("HOME"), ".android"),
    "tooltool_cache_path": os.path.join(os.getenv("HOME"), "cache"),
    "default_actions": [
        'clobber',
        'download-cacheable-artifacts',
        'setup-avds',
        'start-emulators',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-tests',
        'stop-emulators',
    ],
}
