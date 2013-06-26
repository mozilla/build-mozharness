# This is a template config file for b2g emulator unittest testing

config = {
    # mozharness script options
    "xre_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/cba263cef46b57585334f4b71fbbd15ce740fa4b7260571a9f7a76f8f0d6b492b93b01523cb01ee54697cc9b1de1ccc8e89ad64da95a0ea31e0f119fe744c09f",

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
