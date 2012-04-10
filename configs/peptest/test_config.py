import os

config = {
    # mozharness script options
    "log_name": "pep",
    "test_url": "ftp://ftp.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux/1323881237/firefox-11.0a1.en-US.linux-i686.tests.zip",

    # peptest options
    "appname": "ftp://ftp.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux/1323881237/firefox-11.0a1.en-US.linux-i686.tar.bz2",
    "app": "firefox",
    "test_manifest": "tests/firefox/firefox_all.ini", # this is relative to the test folder specified by test_url
    "profile_path": None,
    "timeout": 60,
    "server_path": None,
    "server_port": None,
    "tracer_threshold": 50,
    "tracer_interval": 10,
    "symbols_path": None,
}
