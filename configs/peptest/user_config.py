# This is a template config file for peptest user

# The peptest mozharness script is set up so that specifying None
# is the same as not specifying the option at all
import os

config = {
    # mozharness script options
    "log_name": "pep",
    "log_level": "info",
    "test_url": "url_to_packaged_tests",
    # path or url to a zip or folder containing the mozbase packages
    "mozbase_url": "url_to_mozbase_zip",
    # path or url to a zip or folder containing peptest
    "peptest_url": "url_to_peptest_zip",

    # peptest options

    "appname": "path_to_application_binary",
    # defaults to firefox, can also be thunderbird, fennec, etc.
    "app": "firefox",
    "test_manifest": "path_to_test_manifest",
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
}
