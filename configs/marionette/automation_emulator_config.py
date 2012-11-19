# This is a template config file for marionette production.

EMULATOR_MANIFEST = """[{
"size": 622054113,
"digest": "920f00abcc52c8f475dc861d4a4d7a4f4b8ff309f16926c8c780602e5f41ed7c7e79c9bc68076fd4641520ce1b3803c64fd4e3f60bf9081a9e6529b4aee1bff9",
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

