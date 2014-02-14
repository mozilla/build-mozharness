import os

config = {
    "buildbot_json_path": "buildprops.json",
    "host_utils_url": "http://bm-remote.build.mozilla.org/tegra/tegra-host-utils.Linux.742597.zip",
    "robocop_package_name": "org.mozilla.roboexample.test",
    "device_ip": "127.0.0.1",
    "default_sut_port1": "20701",
    "default_sut_port2": "20700", # does not prompt for commands
    "tooltool_url": "http://tooltool.pvt.build.mozilla.org/build/sha512",
    "tooltool_cache_path": "/builds/slave/talos-slave/cached",
    "tooltool_cacheable_artifacts": {
        "avd_tar_ball": ("AVDs-armv7a-gingerbread-build-2014-01-23-ubuntu.tar.gz",
            "7140e026b7b747236545dc30e377a959b0bdf91bb4d70efd7f97f92fce12a9196042503124b8df8d30c2d97b7eb5f9df9556afdffa0b5d9625008aead305c32b"),
    },
    ".avds_dir": "/home/cltbld/.android",
    "emulator_process_name": "emulator64-arm",
    "emulator_cpu": "cortex-a9",
    "exes": {
        'adb': '/tools/android-sdk18/platform-tools/adb',
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },
    "env": {
        "DISPLAY": ":0.0",
        "PATH": "%(PATH)s:/tools/android-sdk18/tools:/tools/android-sdk18/platform-tools",
        "MINIDUMP_STACKWALK": "/home/cltbld/talos-slave/test/build/venv/lib/python2.7/site-packages/talos/breakpad/linux64/minidump_stackwalk",
        "MINIDUMP_SAVEPATH": "%(abs_work_dir)s/../minidumps"
    },
    "default_actions": [
        'clobber',
        'read-buildbot-config',
        'download-cacheable-artifacts',
        'setup-avds',
        'start-emulators',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-tests',
        'stop-emulators',
    ],
    "emulators": [
        {
            "name": "test-1",
            "device_id": "emulator-5554",
            "http_port": "8854", # starting http port to use for the mochitest server
            "ssl_port": "4454", # starting ssl port to use for the server
            "emulator_port": 5554,
            "sut_port1": 20701,
            "sut_port2": 20700
        },
        {
            "name": "test-2",
            "device_id": "emulator-5556",
            "http_port": "8856", # starting http port to use for the mochitest server
            "ssl_port": "4456", # starting ssl port to use for the server
            "emulator_port": 5556,
            "sut_port1": 20703,
            "sut_port2": 20702
        },
        {
            "name": "test-3",
            "device_id": "emulator-5558",
            "http_port": "8858", # starting http port to use for the mochitest server
            "ssl_port": "4458", # starting ssl port to use for the server
            "emulator_port": 5558,
            "sut_port1": 20705,
            "sut_port2": 20704
        },
        {
            "name": "test-4",
            "device_id": "emulator-5560",
            "http_port": "8860", # starting http port to use for the mochitest server
            "ssl_port": "4460", # starting ssl port to use for the server
            "emulator_port": 5560,
            "sut_port1": 20707,
            "sut_port2": 20706
        }
    ],
    "test_suite_definitions": {
        "jsreftest": {
            "category": "reftest",
            "extra_args": ["../jsreftest/tests/jstests.list",
                "--extra-profile-file=jsreftest/tests/user.js"]
        },
        "mochitest-1": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "10", "--this-chunk", "1", "--run-only-tests", "android.json"],
        },
        "mochitest-2": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "10", "--this-chunk", "2", "--run-only-tests", "android.json"],
        },
        "mochitest-3": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "10", "--this-chunk", "3", "--run-only-tests", "android.json"],
        },
        "mochitest-4": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "10", "--this-chunk", "4", "--run-only-tests", "android.json"],
        },
        "mochitest-5": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "10", "--this-chunk", "5", "--run-only-tests", "android.json"],
        },
        "mochitest-6": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "10", "--this-chunk", "6", "--run-only-tests", "android.json"],
        },
        "mochitest-7": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "10", "--this-chunk", "7", "--run-only-tests", "android.json"],
        },
        "mochitest-8": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "10", "--this-chunk", "8", "--run-only-tests", "android.json"],
        },
        "mochitest-9": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "10", "--this-chunk", "9", "--run-only-tests", "android.json"],
        },
        "mochitest-10": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "10", "--this-chunk", "10", "--run-only-tests", "android.json"],
        },
        "mochitest-gl": {
            "category": "mochitest",
            "extra_args": ["--test-path", "content/canvas/test/webgl"],
        },
        "reftest-1": {
            "category": "reftest",
            "extra_args": ["--total-chunks", "3", "--this-chunk", "1",
                "tests/layout/reftests/reftest.list"]
        },
        "reftest-2": {
            "category": "reftest",
            "extra_args": ["--total-chunks", "3", "--this-chunk", "2",
                "tests/layout/reftests/reftest.list"]
        },
        "reftest-3": {
            "category": "reftest",
            "extra_args": ["--total-chunks", "3", "--this-chunk", "3",
                "tests/layout/reftests/reftest.list"]
        },
        "crashtest-1": {
            "category": "reftest",
            "extra_args": ["--total-chunks", "4", "--this-chunk", "1",
                "tests/testing/crashtest/crashtests.list"]
        },
        "crashtest-2": {
            "category": "reftest",
            "extra_args": ["--total-chunks", "4", "--this-chunk", "2",
                "tests/testing/crashtest/crashtests.list"]
        },
        "crashtest-3": {
            "category": "reftest",
            "extra_args": ["--total-chunks", "4", "--this-chunk", "3",
                "tests/testing/crashtest/crashtests.list"]
        },
        "crashtest-4": {
            "category": "reftest",
            "extra_args": ["--total-chunks", "4", "--this-chunk", "4",
                "tests/testing/crashtest/crashtests.list"]
        },
        "xpcshell-1": {
            "category": "xpcshell",
            "extra_args": ["--total-chunks", "3", "--this-chunk", "1",
                "--manifest", "tests/xpcshell_android.ini"]
        },
        "xpcshell-2": {
            "category": "xpcshell",
            "extra_args": ["--total-chunks", "3", "--this-chunk", "2",
                "--manifest", "tests/xpcshell_android.ini"]
        },
        "xpcshell-3": {
            "category": "xpcshell",
            "extra_args": ["--total-chunks", "3", "--this-chunk", "3",
                "--manifest", "tests/xpcshell_android.ini"]
        },
        "robocop-1": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "4", "--this-chunk", "1", "--robocop-path=../..",
                "--robocop-ids=fennec_ids.txt", "--robocop=robocop.ini"],
        },
        "robocop-2": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "4", "--this-chunk", "2", "--robocop-path=../..",
                "--robocop-ids=fennec_ids.txt", "--robocop=robocop.ini"],
        },
        "robocop-3": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "4", "--this-chunk", "3", "--robocop-path=../..",
                "--robocop-ids=fennec_ids.txt", "--robocop=robocop.ini"],
        },
        "robocop-4": {
            "category": "mochitest",
            "extra_args": ["--total-chunks", "4", "--this-chunk", "4", "--robocop-path=../..",
                "--robocop-ids=fennec_ids.txt", "--robocop=robocop.ini"],
        },
    }, # end of "test_definitions"
    "suite_definitions": {
        "mochitest": {
            "run_filename": "runtestsremote.py",
            "options": ["--autorun", "--close-when-done", "--dm_trans=sut",
                "--console-level=INFO", "--app=%(app)s", "--remote-webserver=%(remote_webserver)s",
                "--xre-path=%(xre_path)s", "--utility-path=%(utility_path)s",
                "--deviceIP=%(device_ip)s", "--devicePort=%(device_port)s",
                "--http-port=%(http_port)s", "--ssl-port=%(ssl_port)s",
                "--certificate-path=%(certs_path)s", "--symbols-path=%(symbols_path)s"
            ],
        },
        "reftest": {
            "run_filename": "remotereftest.py",
            "options": [ "--app=%(app)s", "--ignore-window-size",
                "--bootstrap", "--enable-privilege",
                "--remote-webserver=%(remote_webserver)s", "--xre-path=%(xre_path)s",
                "--utility-path=%(utility_path)s", "--deviceIP=%(device_ip)s",
                "--devicePort=%(device_port)s", "--http-port=%(http_port)s",
                "--ssl-port=%(ssl_port)s", "--httpd-path", "reftest/components",
                "--symbols-path=%(symbols_path)s",
            ],
        },
        "xpcshell": {
            "run_filename": "remotexpcshelltests.py",
            "options": ["--deviceIP=%(device_ip)s", "--devicePort=%(device_port)s",
                "--xre-path=%(xre_path)s", "--testing-modules-dir=%(modules_dir)s",
                "--apk=%(installer_path)s", "--no-logfiles",
                "--symbols-path=%(symbols_path)s",
            ],
        },
    }, # end of "suite_definitions"
}
