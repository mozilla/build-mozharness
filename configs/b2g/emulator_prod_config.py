# This is a template config file for b2g emulator unittest production.

config = {
    # mozharness options
    "application": "b2g",
    "emulator_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/66f9f7f58a100b67d151e64d4c9069dc06105cbf08a10170c341100154c4999708f0304530d7adffbc0ce84c18cdd9f2b49b21365fa8f08b73027e424c4ce68b",
    "xpcshell_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/7c349ae926492bd67bd861f23013d5dd1ad14966bc5da314c6036ddd8db53c119db909a6a22718a0794c56d1f2d8c1742be067489f29e2066d9a5eee823b403a",

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
