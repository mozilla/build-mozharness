# This is a template config file for b2g emulator unittest production.

config = {
    # mozharness options
    "application": "b2g",
    "emulator_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/69cba761fc84f8db3b5f536c60027b6515acd5b3084156c67319bdb8e18b06170aedff64333692a80ea1ef8f9c5bdc6fc688b559703b59b5071aebb1bd6ffddf",
    "xpcshell_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/372c89f9dccaf5ee3b9d35fd1cfeb089e1e5db3ff1c04e35aa3adc8800bc61a2ae10e321f37ae7bab20b56e60941f91bb003bcb22035902a73d70872e7bd3282",

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
