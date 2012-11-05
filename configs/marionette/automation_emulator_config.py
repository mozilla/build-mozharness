# This is a template config file for marionette production.

config = {
    # marionette options
    "test_type": "b2g",
    "emulator": "arm",
    "emulator_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/3ca539707168eb09a468376d9054fbfbeafdeecbc75f071f80537cfa6f8f98a134c605d61d31a1337ed0d4bb15e6acce3fbaa275b08da17612470c9db63e015d",
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

