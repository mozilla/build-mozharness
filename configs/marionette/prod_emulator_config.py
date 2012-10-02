# This is a template config file for marionette production.

config = {
    # marionette options
    "type": "b2g",
    "emulator": "arm",
    "emulator_path": "/path/to/emulator",
    "emulator_url": "http://url/to/emulator",
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

