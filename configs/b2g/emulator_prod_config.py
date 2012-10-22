# This is a template config file for b2g emulator unittest production.

config = {
    # mozharness options
    "application": "b2g",
    "emulator_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/66f9f7f58a100b67d151e64d4c9069dc06105cbf08a10170c341100154c4999708f0304530d7adffbc0ce84c18cdd9f2b49b21365fa8f08b73027e424c4ce68b",
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
        'run-tests',
    ],
}
