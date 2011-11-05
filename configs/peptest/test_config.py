import os

config = {
    # mozharness script options
    "base_work_dir": os.getcwd(),
    "work_dir": "build",
    "log_name": "pep",
    "log_level": "info",
    "test_url": "https://github.com/downloads/ahal/peptest/tests.zip",
    "mozbase_path": "https://github.com/mozilla/mozbase/zipball/master",
    "peptest_path": "https://github.com/mozilla/peptest/zipball/master",

    # peptest options
    "appname": "ftp://ftp.mozilla.org/pub/firefox/nightly/latest-mozilla-central/firefox-10.0a1.en-US.linux-i686.tar.bz2",
    "app": "firefox",
    "test_manifest": "firefox/all_tests.ini", # this is relative to the test folder specified by test_url
    "profile_path": None,
    "timeout": 60,
    "server_path": None,
    "server_port": None,
    "tracer_threshold": 50,
    "tracer_interval": 10,
    "symbols_path": None,

    # get latest tinderbox options
    "get_latest_tinderbox_product": "mozilla-central",
    "get_latest_tinderbox_platform": None,
    "get_latest_tinderbox_debug_build": False,
}

abs_work_dir = os.path.abspath(os.path.join(config['base_work_dir'],
                                            config['work_dir']))

config['virtualenv_path'] = os.path.join(abs_work_dir, "venv")
config['test_install_dir'] = os.path.join(abs_work_dir, "tests")
config['application_install_dir'] = os.path.join(abs_work_dir,
                                                 "application")
