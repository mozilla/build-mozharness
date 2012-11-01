# This is a template config file for marionette production.

config = {
    # marionette options
    "test_type": "b2g",
    "emulator": "arm",
    "emulator_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/66f9f7f58a100b67d151e64d4c9069dc06105cbf08a10170c341100154c4999708f0304530d7adffbc0ce84c18cdd9f2b49b21365fa8f08b73027e424c4ce68b",
    "test_manifest": "unit-tests.ini",

    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },

    "find_links": ["http://puppetagain.pub.build.mozilla.org/data/python/packages"],

    "buildbot_json_path": "buildprops.json",

    "default_actions": [
        'clobber',
        'read-buildbot-config',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-marionette',
    ],
}

