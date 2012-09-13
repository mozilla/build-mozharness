# This is a template config file for marionette production on Windows.

config = {
    # marionette options
    "type": "browser",
    "marionette_address": "localhost:2828",
    "test_manifest": "unit-tests.ini",

    "virtualenv_python_dll": 'c:/mozilla-build/python27/python27.dll',
    "virtualenv_path": 'c:/talos-slave/test/build/venv',
    "exes": {
        'python': 'c:/mozilla-build/python27/python',
        'virtualenv': ['c:/mozilla-build/python27/python', 'c:/mozilla-build/buildbotve/virtualenv.py'],
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
