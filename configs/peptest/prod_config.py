# This is a template config file for peptest production

# The peptest mozharness script is set up so that specifying None
# is the same as not specifying the option at all

config = {
    # mozharness script options
    "log_name": "pep",
    "buildbot_json_path": "buildprops.json",
    "simplejson_url": "http://talos-bundles.pvt.build.mozilla.org/zips/simplejson-2.2.1.tar.gz",
    # tp5n url used by talos
    "tp5n_url": "http://talos-bundles.pvt.build.mozilla.org/zips/tp5n.zip",

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
    "server_proxy": "tests/firefox/server-locations.txt",
    "server_path": "tests/firefox/server",
    "server_port": None,
    # EventTracer setting, the threshold to count a failure (ms)
    "tracer_threshold": 0,
    # EventTracer setting, interval at which to send tracer events (ms)
    "tracer_interval": 10,
    # URL or path to the symbols directory for debugging crashes
    "symbols_path": None,
    # number of times the entire test suite is run
    "iterations": 10,

    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },

    "default_actions": [
        "clobber",
        "read-buildbot-config",
        "download-and-extract",
        "create-virtualenv",
        "install",
        "install-tp5n",
        "run-peptest",
    ],
}
