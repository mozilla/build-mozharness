config = {
    "log_name": "talos",
    "base_work_dir": "/src/talosrunner/tegra_bwd",

    "installer_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/nightly/latest-mozilla-central-android/fennec-15.0a1.en-US.android-arm.apk",
    "pypi_url": "http://people.mozilla.com/~jhammel/pypi/",
    "device_name": "tegra-031",
    "device_package_name": "org.mozilla.fennec",
    "talos_device_name": "tegra-031",

    # set graph_server to a real graph server if you want to publish your
    # results (the device needs to be in the database already or you'll
    # get errors)
    "graph_server": "graphs-stage.mozilla.org",

    "results_link": "/server/collect.cgi",
    "talos_suites": ["tsvg"],
    "talos_config_file": "remote.config",

    # this needs to be set to either your_IP:8000, or an existing webserver
    # that serves talos.
#    "talos_webserver": "10.251.25.44:8000",
    "talos_webserver": "bm-remote.build.mozilla.org",

    # adb or sut
    "device_protocol": "sut",

    # set this to >0 if you want devicemanager output.
    # beware, this will send binary characters to your terminal
#    "devicemanager_debug_level": 2,

    # set this for adb-over-ip or sut.
    "device_ip": "10.250.49.18",

    # setting this to tegra250 will add tegra-specific behavior
    "device_type": "tegra250",

    # enable_automation will run steps that may be undesirable for the
    # average user.
    "enable_automation": True,

#    "actions": ["check-device"],
#    "no_actions": ["preclean", "pull", "download", "unpack"],
}
