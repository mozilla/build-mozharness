# This is a template config file for b2g emulator unittest testing

config = {
    # mozharness script options
    "xre_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/d4297e762649b174070a33d039fd062edd9f29a751650f0508327a6cf366b3a35fe24e7cd0f7b728d74f7d15399f9c1adc5b178e5803a3a66bfce7a8dcd62daa",

    # mozharness configuration
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],

    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
        'tooltool.py': "/tools/tooltool.py",
    },

    "find_links": ["http://repos/python/packages"],
    "pip_index": False,

    "buildbot_json_path": "buildprops.json",

    "default_actions": [
        'clobber',
        'read-buildbot-config',
        'pull',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'make-gaia',
        'run-tests',
    ],
}
