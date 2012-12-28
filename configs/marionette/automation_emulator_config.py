# This is a template config file for marionette production.

EMULATOR_MANIFEST = """[{
"size": 615398796,
"digest": "db59094fb366ddb407083edb19ee695146d70a5c110e088f22349148e3d314a0d6261272e1781a5404db2e5bc6dc4be283c5eb76b4ebb32193f2f099ac343ca5",
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

