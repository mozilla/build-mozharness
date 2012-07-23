config = {
    "log_name": "talos",
    "base_work_dir": "/src/talosrunner/tablet_bwd",

    "installer_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/nightly/latest-mozilla-central-android/fennec-15.0a1.en-US.android-arm.apk",
    "pypi_url": "http://people.mozilla.com/~jhammel/pypi/",
    "device_name": "aki_tablet",
    "device_package_name": "org.mozilla.fennec",

    # set graph_server to "''" to not use a graph_server
#    "graph_server": "graphs-stage.mozilla.org",
    "graph_server": "''",

    "results_link": "/server/collect.cgi",
    "talos_suites": ["tsvg"],
    "talos_config_file": "remote.config",

    # this needs to be set to either your_IP:8000, or an existing webserver
    # that serves talos.
    "talos_webserver": "10.251.25.44:8000",

    # Set this to start a webserver automatically
    "start_python_webserver": True,

    # adb or sut
    "device_protocol": "adb",

    # set this for adb-over-ip or sut.
    "device_ip": "10.251.28.128",

    # setting this to tegra250 will add tegra-specific behavior
    "device_type": "non-tegra",

    # enable_automation will run steps that may be undesirable for the
    # average user.
    "enable_automation": True,

#    "actions": ["check-device"],
#    "no_actions": ["preclean", "pull", "download", "unpack"],
}
