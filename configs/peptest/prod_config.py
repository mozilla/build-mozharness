# This is a template config file for peptest production

# The peptest mozharness script is set up so that specifying None
# is the same as not specifying the option at all

config = {
    # mozharness script options
    "log_name": "pep",
    "buildbot_json_path": "buildprops.json",
    "virtualenv_modules": ["simplejson"],
    "simplejson_url": "http://build.mozilla.org/talos/zips/simplejson-2.2.1.tar.gz",
    # peptest options
    # defaults to firefox, can also be thunderbird, fennec, etc.
    "app": "firefox",
    # if test_url is specified, this should be the relative
    # path to the manifest inside the extracted test directory
    # otherwise, should be path to a test manifest on the local file system
    "test_manifest": "tests/firefox/firefox_all.ini",
    # optional, use an existing profile (temp profile created by default)
    "profile_path": None,
    # global timeout in seconds (without output)
    "timeout": 60,
    # if specified, creates a webserver for hosting test
    # related files at this document root
    "server_path": None,
    "server_port": None,
    # EventTracer setting, the threshold to count a failure (ms)
    "tracer_threshold": 50,
    # EventTracer setting, interval at which to send tracer events (ms)
    "tracer_interval": 10,
    # URL or path to the symbols directory for debugging crashes
    "symbols_path": None,

    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },

    "default_actions": [
        "clobber",
        "create-virtualenv",
        "read-buildbot-config",
        "create-deps",
        "run-peptest",
    ],
    "repos": [{"repo": "http://hg.mozilla.org/build/tools",}],
}
