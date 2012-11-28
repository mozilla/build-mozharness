# This is a template config file for marionette production.

EMULATOR_MANIFEST = """[{
"size": 616293696,
"digest": "d45d05f83804991eea7ecc95c801d0de17809532e3e770dbd491445de05b451155f33859139952a69d156d1b402f7366f942e5790561b1a3008d83af4144ca02",
"algorithm": "sha512",
"filename": "emulator.zip"
}]
"""

config = {
    # marionette options
    "test_type": "b2g",
    "emulator": "arm",
    "emulator_manifest": EMULATOR_MANIFEST,
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],
    "test_manifest": "unit-tests.ini",

    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
        'tooltool.py': "/tools/tooltool.py",
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

