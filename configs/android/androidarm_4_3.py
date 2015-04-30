import os

config = {
    "buildbot_json_path": "buildprops.json",
    "host_utils_url": "http://talos-remote.pvt.build.mozilla.org/tegra/tegra-host-utils.Linux.1109310.2.zip",
    "robocop_package_name": "org.mozilla.roboexample.test",
    "tooltool_manifest_path": "testing/config/tooltool-manifests/androidarm_4_3/releng.manifest",
    "tooltool_cache": "/builds/tooltool_cache",
    ".avds_dir": "/home/cltbld/.android",
    "emulator_manifest": """
        [
        {
        "size": 140097024,
        "digest": "51781032335c09103e8509b1a558bf22a7119392cf1ea301c49c01bdf21ff0ceb37d260bc1c322cd9b903252429fb01830fc27e4632be30cd345c95bf4b1a39b",
        "algorithm": "sha512",
        "filename": "android-sdk_r24.0.2-linux.tgz",
        "unpack": "True"
        }
        ] """,
    "tools_manifest": """
        [
        {
        "size": 193383673,
        "digest": "6609e8b95db59c6a3ad60fc3dcfc358b2c8ec8b4dda4c2780eb439e1c5dcc5d550f2e47ce56ba14309363070078d09b5287e372f6e95686110ff8a2ef1838221",
        "algorithm": "sha512",
        "filename": "android-sdk18_0.r18moz1.orig.tar.gz",
        "unpack": "True"
        }
        ] """,
    "emulator_process_name": "emulator64-arm",
    "emulator_extra_args": "-debug init,console,gles,memcheck,adbserver,adbclient,adb,avd_config,socket",
    "device_manager": "adb",
    "exes": {
        'adb': '%(abs_work_dir)s/android-sdk18/platform-tools/adb',
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
        'tooltool.py': "/tools/tooltool.py",
    },
    "env": {
        "DISPLAY": ":0.0",
        "PATH": "%(PATH)s:%(abs_work_dir)s/android-sdk-linux/tools:%(abs_work_dir)s/android-sdk18/platform-tools",
        "MINIDUMP_SAVEPATH": "%(abs_work_dir)s/../minidumps"
    },
    "default_actions": [
        'clobber',
        'read-buildbot-config',
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
        },
    ],
    "test_suite_definitions": {
        "jsreftest-1": {
            "category": "jsreftest",
            "extra_args": ["--this-chunk=1"],
        },
        "jsreftest-2": {
            "category": "jsreftest",
            "extra_args": ["--this-chunk=2"],
        },
        "jsreftest-3": {
            "category": "jsreftest",
            "extra_args": ["--this-chunk=3"],
        },
        "jsreftest-4": {
            "category": "jsreftest",
            "extra_args": ["--this-chunk=4"],
        },
        "jsreftest-5": {
            "category": "jsreftest",
            "extra_args": ["--this-chunk=5"],
        },
        "jsreftest-6": {
            "category": "jsreftest",
            "extra_args": ["--this-chunk=6"],
        },
        "jsreftest-7": {
            "category": "jsreftest",
            "extra_args": ["--this-chunk=7"],
        },
        "jsreftest-8": {
            "category": "jsreftest",
            "extra_args": ["--this-chunk=8"],
        },
        "mochitest-1": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=1"],
        },
        "mochitest-2": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=2"],
        },
        "mochitest-3": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=3"],
        },
        "mochitest-4": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=4"],
        },
        "mochitest-5": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=5"],
        },
        "mochitest-6": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=6"],
        },
        "mochitest-7": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=7"],
        },
        "mochitest-8": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=8"],
        },
        "mochitest-9": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=9"],
        },
        "mochitest-10": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=10"],
        },
        "mochitest-11": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=11"],
        },
        "mochitest-12": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=12"],
        },
        "mochitest-13": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=13"],
        },
        "mochitest-14": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=14"],
        },
        "mochitest-15": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=15"],
        },
        "mochitest-16": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=16"],
        },
        "mochitest-17": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=17"],
        },
        "mochitest-18": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=18"],
        },
        "mochitest-19": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=19"],
        },
        "mochitest-20": {
            "category": "mochitest",
            "extra_args": ["--this-chunk=20"],
        },
        "mochitest-gl-1": {
            "category": "mochitest-gl",
            "extra_args": ["--this-chunk=1"],
        },
        "mochitest-gl-2": {
            "category": "mochitest-gl",
            "extra_args": ["--this-chunk=2"],
        },
        "mochitest-gl-3": {
            "category": "mochitest-gl",
            "extra_args": ["--this-chunk=3"],
        },
        "mochitest-gl-4": {
            "category": "mochitest-gl",
            "extra_args": ["--this-chunk=4"],
        },
        "reftest-1": {
            "category": "reftest",
            "extra_args": ["--this-chunk=1"],
        },
        "reftest-2": {
            "category": "reftest",
            "extra_args": ["--this-chunk=2"],
        },
        "reftest-3": {
            "category": "reftest",
            "extra_args": ["--this-chunk=3"],
        },
        "reftest-4": {
            "category": "reftest",
            "extra_args": ["--this-chunk=4"],
        },
        "reftest-5": {
            "category": "reftest",
            "extra_args": ["--this-chunk=5"],
        },
        "reftest-6": {
            "category": "reftest",
            "extra_args": ["--this-chunk=6"],
        },
        "reftest-7": {
            "category": "reftest",
            "extra_args": ["--this-chunk=7"],
        },
        "reftest-8": {
            "category": "reftest",
            "extra_args": ["--this-chunk=8"],
        },
        "reftest-9": {
            "category": "reftest",
            "extra_args": ["--this-chunk=9"],
        },
        "reftest-10": {
            "category": "reftest",
            "extra_args": ["--this-chunk=10"],
        },
        "reftest-11": {
            "category": "reftest",
            "extra_args": ["--this-chunk=11"],
        },
        "reftest-12": {
            "category": "reftest",
            "extra_args": ["--this-chunk=12"],
        },
        "reftest-13": {
            "category": "reftest",
            "extra_args": ["--this-chunk=13"],
        },
        "reftest-14": {
            "category": "reftest",
            "extra_args": ["--this-chunk=14"],
        },
        "reftest-15": {
            "category": "reftest",
            "extra_args": ["--this-chunk=15"],
        },
        "reftest-16": {
            "category": "reftest",
            "extra_args": ["--this-chunk=16"],
        },
        "reftest-17": {
            "category": "reftest",
            "extra_args": ["--this-chunk=17"],
        },
        "reftest-18": {
            "category": "reftest",
            "extra_args": ["--this-chunk=18"],
        },
        "reftest-19": {
            "category": "reftest",
            "extra_args": ["--this-chunk=19"],
        },
        "reftest-20": {
            "category": "reftest",
            "extra_args": ["--this-chunk=20"],
        },
        "crashtest-1": {
            "category": "crashtest",
            "extra_args": ["--this-chunk=1"],
        },
        "crashtest-2": {
            "category": "crashtest",
            "extra_args": ["--this-chunk=2"],
        },
        "xpcshell-1": {
            "category": "xpcshell",
            "extra_args": ["--this-chunk=1"],
        },
        "xpcshell-2": {
            "category": "xpcshell",
            "extra_args": ["--this-chunk=2"],
        },
        "xpcshell-3": {
            "category": "xpcshell",
            "extra_args": ["--this-chunk=3"],
        },
        "xpcshell-4": {
            "category": "xpcshell",
            "extra_args": ["--this-chunk=4"],
        },
        "xpcshell-5": {
            "category": "xpcshell",
            "extra_args": ["--this-chunk=5"],
        },
        "xpcshell-6": {
            "category": "xpcshell",
            "extra_args": ["--this-chunk=6"],
        },
        "robocop-1": {
            "category": "robocop",
            "extra_args": ["--this-chunk=1"],
        },
        "robocop-2": {
            "category": "robocop",
            "extra_args": ["--this-chunk=2"],
        },
        "robocop-3": {
            "category": "robocop",
            "extra_args": ["--this-chunk=3"],
        },
        "robocop-4": {
            "category": "robocop",
            "extra_args": ["--this-chunk=4"],
        },
        "robocop-5": {
            "category": "robocop",
            "extra_args": ["--this-chunk=5"],
        },
        "robocop-6": {
            "category": "robocop",
            "extra_args": ["--this-chunk=6"],
        },
        "robocop-7": {
            "category": "robocop",
            "extra_args": ["--this-chunk=7"],
        },
        "robocop-8": {
            "category": "robocop",
            "extra_args": ["--this-chunk=8"],
        },
        "cppunittest": {
            "category": "cppunittest",
            "extra_args": [],
        },
    }, # end of "test_definitions"
    # test harness options are located in the gecko tree
    "in_tree_config": "config/mozharness/android_arm_4_3_config.py",
    "download_minidump_stackwalk": True,
    "default_blob_upload_servers": [
         "https://blobupload.elasticbeanstalk.com",
    ],
    "blob_uploader_auth_file" : os.path.join(os.getcwd(), "oauth.txt"),
}
