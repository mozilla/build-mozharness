# This is a template config file for marionette production.

EMULATOR_MANIFEST = """[{
"size": 628454105,
"digest": "4523bcf9bbb14631ead014cd6f3662bfce1b90981dde43b680b0a68e606fa6e1e05f43efd9fd69436b733f819ccd812a8a7ad8af0834241826eca1396b0ef10a",
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

