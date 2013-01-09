# This is a template config file for marionette production.

EMULATOR_MANIFEST = """[{
"size": 614786766,
"digest": "c17f86729db5d5620cabde893df8c3130d8d23526bb4ef2f5147e7fb7ad5b046e3443019829ee0d58c65ccdb52fc278289c149d7f69c49b8b192ab219c2173d8",
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

