# This is a template config file for b2g emulator unittest production.

EMULATOR_MANIFEST = """[{
"size": 622054113,
"digest": "920f00abcc52c8f475dc861d4a4d7a4f4b8ff309f16926c8c780602e5f41ed7c7e79c9bc68076fd4641520ce1b3803c64fd4e3f60bf9081a9e6529b4aee1bff9",
"algorithm": "sha512",
"filename": "emulator.zip"
}]
"""

config = {
    # mozharness options
    "application": "b2g",
    "emulator_manifest": EMULATOR_MANIFEST,
    "xpcshell_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/d4297e762649b174070a33d039fd062edd9f29a751650f0508327a6cf366b3a35fe24e7cd0f7b728d74f7d15399f9c1adc5b178e5803a3a66bfce7a8dcd62daa",
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],

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
        'run-tests',
    ],
}
