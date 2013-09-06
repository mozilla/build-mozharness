# This is a template config file for panda android tests on production.
import socket


MINIDUMP_STACKWALK_PATH = "/builds/minidump_stackwalk"

config = {
    # Values for the foopies
    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },
    "run_file_names": {
        "mochitest": "runtestsremote.py",
        "reftest": "remotereftest.py",
        "crashtest": "remotereftest.py",
        "jsreftest": "remotereftest.py",
        "robocop": "runtestsremote.py",
        "xpcshell": "remotexpcshelltests.py",
        "jittest": "jit_test.py"
    },
    "hostutils_url":  "http://bm-remote.build.mozilla.org/tegra/tegra-host-utils.Linux.742597.zip",
    "verify_path":  "/builds/sut_tools/verify.py",
    "install_app_path":  "/builds/sut_tools/installApp.py",
    "mochitest_options": [
        "--deviceIP=%(device_ip)s",
        "--xre-path=../hostutils/xre",
        "--utility-path=../hostutils/bin", "--certificate-path=certs",
        "--app=%(app_name)s", "--console-level=INFO",
        "--http-port=%(http_port)s", "--ssl-port=%(ssl_port)s",
        "--run-only-tests=android.json", "--symbols-path=%(symbols_path)s"
    ],
    # reftests other than crashtests or jsreftests not currently run on pandas
    "reftest_options": [
        "--deviceIP=%(device_ip)s",
        "--xre-path=../hostutils/xre",
        "--utility-path=../hostutils/bin",
        "--app=%(app_name)s", "--ignore-window-size",
        "--http-port=%(http_port)s", "--ssl-port=%(ssl_port)s",
        "--symbols-path=%(symbols_path)s",
        "reftest/tests/layout/reftests/reftest.list"
    ],
    "crashtest_options": [
        "--deviceIP=%(device_ip)s",
        "--xre-path=../hostutils/xre",
        "--utility-path=../hostutils/bin",
        "--app=%(app_name)s",
        "--enable-privilege", "--ignore-window-size", "--bootstrap",
        "--http-port=%(http_port)s", "--ssl-port=%(ssl_port)s",
        "--symbols-path=%(symbols_path)s",
        "reftest/tests/testing/crashtest/crashtests.list"
    ],
    "jsreftest_options": [
        "--deviceIP=%(device_ip)s",
        "--xre-path=../hostutils/xre",
        "--utility-path=../hostutils/bin",
        "--app=%(app_name)s",
        "--enable-privilege", "--ignore-window-size", "--bootstrap",
        "--extra-profile-file=jsreftest/tests/user.js", "jsreftest/tests/jstests.list",
        "--http-port=%(http_port)s", "--ssl-port=%(ssl_port)s",
        "--symbols-path=%(symbols_path)s"
    ],
    "robocop_options": [
        "--deviceIP=%(device_ip)s",
        "--xre-path=../hostutils/xre",
        "--utility-path=../hostutils/bin",
        "--certificate-path=certs",
        "--app=%(app_name)s", "--console-level=INFO",
        "--http-port=%(http_port)s", "--ssl-port=%(ssl_port)s",
        "--symbols-path=%(symbols_path)s",
        "--robocop=mochitest/robocop.ini"
    ],
    "xpcshell_options": [
        "--deviceIP=%(device_ip)s",
        "--xre-path=../hostutils/xre",
        "--manifest=xpcshell/tests/xpcshell_android.ini",
        "--build-info-json=xpcshell/mozinfo.json",
        "--testing-modules-dir=modules",
        "--local-lib-dir=../fennec",
        "--apk=../%(apk_name)s",
        "--no-logfiles",
        "--symbols-path=%(symbols_path)s"
    ],
    "jittest_options": [
        "bin/js",
        "--remote",
        "--deviceTransport=sut",
        "--deviceIP=%(device_ip)s",
        "--localLib=../tests/bin",
        "--tinderbox"
     ],
    "all_mochitest_suites": {
        "mochitest-1": ["--total-chunks=8", "--this-chunk=1"],
        "mochitest-2": ["--total-chunks=8", "--this-chunk=2"],
        "mochitest-3": ["--total-chunks=8", "--this-chunk=3"],
        "mochitest-4": ["--total-chunks=8", "--this-chunk=4"],
        "mochitest-5": ["--total-chunks=8", "--this-chunk=5"],
        "mochitest-6": ["--total-chunks=8", "--this-chunk=6"],
        "mochitest-7": ["--total-chunks=8", "--this-chunk=7"],
        "mochitest-8": ["--total-chunks=8", "--this-chunk=8"],
        "mochitest-gl": ["--test-path", "content/canvas/test/webgl"],
    },
    "all_reftest_suites": {
        "reftest-1": ["--total-chunks=5", "--this-chunk=1"],
        "reftest-2": ["--total-chunks=5", "--this-chunk=2"],
        "reftest-3": ["--total-chunks=5", "--this-chunk=3"],
        "reftest-4": ["--total-chunks=5", "--this-chunk=4"],
        "reftest-5": ["--total-chunks=5", "--this-chunk=5"],
    },
    "all_crashtest_suites": {
        "crashtest": []
    },
    "all_jsreftest_suites": {
        "jsreftest-1": ["--total-chunks=3", "--this-chunk=1"],
        "jsreftest-2": ["--total-chunks=3", "--this-chunk=2"],
        "jsreftest-3": ["--total-chunks=3", "--this-chunk=3"],
    },
    "all_robocop_suites": {
        #plain is split
        "robocop-1": ["--total-chunks=3", "--this-chunk=1"],
        "robocop-2": ["--total-chunks=3", "--this-chunk=2"],
        "robocop-3": ["--total-chunks=3", "--this-chunk=3"],
    },
    "all_xpcshell_suites": {
        "xpcshell": []
    },
    "all_jittest_suites": {
        "jittest": []
    },
    "find_links": [
        "http://repos/python/packages",
        "http://releng-puppet2.srv.releng.use1.mozilla.com/python/packages/",
        "http://releng-puppet1.srv.releng.use1.mozilla.com/python/packages/",
        "http://releng-puppet2.build.mtv1.mozilla.com/python/packages/",
        "http://releng-puppet2.srv.releng.usw2.mozilla.com/python/packages/",
        "http://releng-puppet1.srv.releng.usw2.mozilla.com/python/packages/",
        "http://releng-puppet2.srv.releng.scl3.mozilla.com/python/packages/",
        "http://releng-puppet2.build.scl1.mozilla.com/python/packages/",
        "http://puppetagain.pub.build.mozilla.org/data/python/packages/",
    ],
    "pip_index": False,
    "buildbot_json_path": "buildprops.json",
    "mobile_imaging_format": "http://mobile-imaging-%03i.p%i.releng.scl1.mozilla.com",
    "mozpool_assignee": socket.gethostname(),
    "default_actions": [
        'clobber',
        'read-buildbot-config',
        'download-and-extract',
        'create-virtualenv',
        'request-device',
        'run-test',
        'close-request',
    ],
    "minidump_stackwalk_path": MINIDUMP_STACKWALK_PATH,
    "minidump_save_path": "%(abs_work_dir)s/../minidumps",
}
