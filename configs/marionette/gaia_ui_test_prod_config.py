# This is a template config file for marionette production.

config = {
    # marionette options
    "test_type": "b2g",
    "marionette_address": "localhost:2828",
    "gaiatest": True,
    "xre_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/d4a0da54e75c27cd2f535e66b586f119ef08b3bde4a9eee03662d296b3434189c542c0a7e7a75954030c04396a9823e22e1f884f5d87c0f4017944cd50ff38de",

    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },

    "find_links": [
        "http://pypi.pvt.build.mozilla.org/pub",
        "http://pypi.pub.build.mozilla.org/pub",
    ],
    "pip_index": False,

    "buildbot_json_path": "buildprops.json",

    "default_actions": [
        'clobber',
        'read-buildbot-config',
        'pull',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-marionette',
    ],
}
