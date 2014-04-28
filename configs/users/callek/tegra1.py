config = {
    "log_name": "talos",
    #"base_work_dir": "",

    "installer_url": "https://ftp-ssl.mozilla.org/pub/mozilla.org/mobile/nightly/latest-mozilla-central-android/en-US/fennec-16.0a1.en-US.android-arm.apk",
    "repository": "https://hg.mozilla.org/mozilla-central",
    "pypi_url": "http://people.mozilla.com/~jwood/pypi/",
    "pywin32_url": "http://people.mozilla.org/~jwood/pypi/pywin32-216.win32-py2.6.exe",
    "device_name": "tegra-224",
    "device_package_name": "org.mozilla.fennec",
    "talos_device_name": "tegra-224",
    "virtualenv_modules": ["pywin32", "talos"],
    "exes": {"easy_install": ['d:\\Sources\\mozharness\\build\\venv\\Scripts\\python.exe',
                              'd:\\Sources\\mozharness\\build\\venv\\scripts\\easy_install-2.6-script.py'], },

    # set graph_server to a real graph server if you want to publish your
    # results (the device needs to be in the database already or you'll
    # get errors)
    "graph_server": "graphs.allizom.org",

    "results_link": "/server/collect.cgi",
    "talos_suites": ["tsvg"],
    "tests": ["tsvg"],
    "talos_config_file": "venv/Lib/site-packages/talos/remote.config",

    # this needs to be set to either your_IP:8000, or an existing webserver
    # that serves talos.
#    "talos_webserver": "10.251.25.44:8000",
    "talos_webserver": "bm-remote.build.mozilla.org",
    "talos_branch": "MobileTest",
    "disable_chrome": True,

    # adb or sut
    "device_protocol": "sut",

    # set this to >0 if you want devicemanager output.
    # beware, this will send binary characters to your terminal
#    "devicemanager_debug_level": 2,

    # set this for adb-over-ip or sut.
    "device_ip": "10.250.51.64",

    # setting this to tegra250 will add tegra-specific behavior
    "device_type": "tegra250",

    # enable_automation will run steps that may be undesirable for the
    # average user.
    "enable_automation": True,

#    "actions": ["check-device"],
#    "no_actions": ["preclean", "pull", "download", "unpack"],
}
