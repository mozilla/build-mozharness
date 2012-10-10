# This is a template config file for marionette production.

config = {
    # marionette options
    "test_type": "b2g",
    "emulator": "arm",
    "emulator_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/69cba761fc84f8db3b5f536c60027b6515acd5b3084156c67319bdb8e18b06170aedff64333692a80ea1ef8f9c5bdc6fc688b559703b59b5071aebb1bd6ffddf",
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

