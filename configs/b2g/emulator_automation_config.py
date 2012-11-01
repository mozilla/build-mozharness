# This is a template config file for b2g emulator unittest production.

config = {
    # mozharness options
    "application": "b2g",
    "emulator_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/575d9c1936d8bc418c6672e8625fa0c7239d9e644da141763d888b8a3fba6913e0a15ecb331fa686906ce4017d81ce5972f5523cc2516581dd7869b17a77d2f6",
    "xpcshell_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/d4297e762649b174070a33d039fd062edd9f29a751650f0508327a6cf366b3a35fe24e7cd0f7b728d74f7d15399f9c1adc5b178e5803a3a66bfce7a8dcd62daa",

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
