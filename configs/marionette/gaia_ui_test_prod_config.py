# This is a template config file for marionette production.

config = {
    # marionette options
    "test_type": "b2g-bluetooth-antenna-carrier-wifi-sdcard-offline-camera-xfail",
    "marionette_address": "localhost:2828",
    "gaiatest": True,

    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },

    "find_links": ["http://repos/python/packages"],
    "pip_index": False,

    "buildbot_json_path": "buildprops.json",

    "default_actions": [
        'clobber',
        'pull',
        'read-buildbot-config',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-marionette',
    ],
}
