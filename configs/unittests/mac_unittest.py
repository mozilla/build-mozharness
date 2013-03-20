import os

#### OS Specifics ####
INSTALLER_PATH = os.path.join(os.getcwd(), "installer.dmg")
XPCSHELL_NAME = 'xpcshell'
DISABLE_SCREEN_SAVER = False
ADJUST_MOUSE_AND_SCREEN = False
#####
config = {
    ### BUILDBOT
    "buildbot_json_path": "buildprops.json",
    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },
    ###
    "installer_path": INSTALLER_PATH,
    "xpcshell_name": XPCSHELL_NAME,
    "simplejson_url": "http://repos/python/packages/simplejson-2.1.3.tar.gz",
    "run_file_names": {
        "mochitest": "runtests.py",
        "reftest": "runreftest.py",
        "xpcshell": "runxpcshelltests.py"
    },
    "minimum_tests_zip_dirs": ["bin/*", "certs/*", "modules/*", "mozbase/*"],
    "specific_tests_zip_dirs": {
        "mochitest": ["mochitest/*"],
        "reftest": ["reftest/*", "jsreftest/*"],
        "xpcshell": ["xpcshell/*"]
    },
    "reftest_options": [
        "--appname=%(binary_path)s", "--utility-path=tests/bin",
        "--extra-profile-file=tests/bin/plugins", "--symbols-path=%(symbols_path)s"
    ],
    "mochitest_options": [
        "--appname=%(binary_path)s", "--utility-path=tests/bin",
        "--extra-profile-file=tests/bin/plugins", "--symbols-path=%(symbols_path)s",
        "--certificate-path=tests/certs", "--autorun", "--close-when-done",
        "--console-level=INFO"
    ],
    "xpcshell_options": [
        "--symbols-path=%(symbols_path)s"
    ],
    #local mochi suites
    "all_mochitest_suites": {
        "plain1": ["--total-chunks=5", "--this-chunk=1", "--chunk-by-dir=4"],
        "plain2": ["--total-chunks=5", "--this-chunk=2", "--chunk-by-dir=4"],
        "plain3": ["--total-chunks=5", "--this-chunk=3", "--chunk-by-dir=4"],
        "plain4": ["--total-chunks=5", "--this-chunk=4", "--chunk-by-dir=4"],
        "plain5": ["--total-chunks=5", "--this-chunk=5", "--chunk-by-dir=4"],
        "chrome": ["--chrome"],
        "browser-chrome": ["--browser-chrome"],
        "a11y": ["--a11y"],
        "plugins": ['--setpref=dom.ipc.plugins.enabled=false',
                    '--setpref=dom.ipc.plugins.enabled.x86_64=false',
                    '--ipcplugins']
    },
    #local reftest suites
    "all_reftest_suites": {
        "reftest": ["tests/reftest/tests/layout/reftests/reftest.list"],
        "crashtest": ["tests/reftest/tests/testing/crashtest/crashtests.list"],
        "jsreftest": ["--extra-profile-file=tests/jsreftest/tests/user.js", "tests/jsreftest/tests/jstests.list"],
        "reftest-ipc": ['--setpref=browser.tabs.remote=true',
                        'tests/reftest/tests/layout/reftests/reftest-sanity/reftest.list'],
        "crashtest-ipc": ['--setpref=browser.tabs.remote=true',
                          'tests/reftest/tests/testing/crashtest/crashtests.list'],
    },
    "all_xpcshell_suites": {
        "xpcshell": ["--manifest=tests/xpcshell/tests/all-test-dirs.list",
        "%(abs_app_dir)s/" + XPCSHELL_NAME]
    },
    "run_cmd_checks_enabled": True,
    "preflight_run_cmd_suites": [
        # NOTE 'enabled' is only here while we have unconsolidated configs
        {
            "name": "disable_screen_saver",
            "cmd": ["xset", "s", "off", "s", "reset"],
            "architectures": ["32bit", "64bit"],
            "halt_on_failure": False,
            "enabled": DISABLE_SCREEN_SAVER
        },
        {
            "name": "run mouse & screen adjustment script",
            "cmd": [
                # when configs are consolidated this python path will only show
                # for windows.
                "python", "../scripts/external_tools/mouse_and_screen_resolution.py",
                "--configuration-url",
                "http://hg.mozilla.org/%(branch)s/raw-file/%(revision)s/" +
                    "testing/machine-configuration.json"],
            "architectures": ["32bit"],
            "halt_on_failure": True,
            "enabled": ADJUST_MOUSE_AND_SCREEN
        },
    ],
    "repos": [{"repo": "http://hg.mozilla.org/build/tools",}],
    "minidump_stackwalk_path": "%(abs_work_dir)s/tools/breakpad/osx64/minidump_stackwalk",
    "minidump_save_path": "%(abs_work_dir)s/../minidumps",
}
