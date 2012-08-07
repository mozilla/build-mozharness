import os

config = {
    # mozharness script options
    "log_name": "pep",
    "test_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-aurora-linux64/1342707676/firefox-16.0a2.en-US.linux-x86_64.tests.zip",
    "tp5n_url": "http://people.mozilla.com/~ahalberstadt/tp5n2.zip",

    # peptest options
    "installer_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-aurora-linux64/1342707676/firefox-16.0a2.en-US.linux-x86_64.tar.bz2",
    "app": "firefox",
    "test_manifest": "tests/firefox/firefox_all.ini", # this is relative to the test folder specified by test_url
    "profile_path": None,
    "timeout": 60,
    "server_path": "tests/firefox/server",
    "server_port": None,
    "server_proxy": "tests/firefox/server-locations.txt",
    "tracer_threshold": 50,
    "tracer_interval": 10,
    "symbols_path": None,
}
