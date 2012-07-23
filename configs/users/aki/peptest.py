import os

config = {
    # mozharness script options
    "log_name": "pep",
    "base_work_dir": os.path.join(os.getcwd(), "peptest"),
    "pypi_url": "http://people.mozilla.com/~jhammel/pypi",
    "test_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central/firefox-15.0a1.en-US.mac.tests.zip",

    # peptest options
    "installer_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central/firefox-15.0a1.en-US.mac.dmg",
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
