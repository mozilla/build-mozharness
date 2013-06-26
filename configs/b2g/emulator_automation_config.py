# This is a template config file for b2g emulator unittest production.

config = {
    # mozharness options
    "application": "b2g",
    "busybox_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/0748e900821820f1a42e2f1f3fa4d9002ef257c351b9e6b78e7de0ddd0202eace351f440372fbb1ae0b7e69e8361b036f6bd3362df99e67fc585082a311fc0df",
    "xre_url": "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/cba263cef46b57585334f4b71fbbd15ce740fa4b7260571a9f7a76f8f0d6b492b93b01523cb01ee54697cc9b1de1ccc8e89ad64da95a0ea31e0f119fe744c09f",
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],

    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
        'tooltool.py': "/tools/tooltool.py",
    },

    "find_links": ["http://repos/python/packages"],
    "pip_index": False,

    "buildbot_json_path": "buildprops.json",

    "default_actions": [
        'clobber',
        'read-buildbot-config',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-tests',
    ],
    "download_symbols": "ondemand",
    "download_minidump_stackwalk": True,

    # test harness options
    "run_file_names": {
        "mochitest": "runtestsb2g.py",
        "reftest": "runreftestb2g.py",
        "crashtest": "runreftestb2g.py",
        "xpcshell": "runtestsb2g.py"
    },

    "mochitest_options": [
        "--adbpath=%(adbpath)s", "--b2gpath=%(b2gpath)s", "--console-level=INFO",
        "--emulator=%(emulator)s", "--logcat-dir=%(logcat_dir)s",
        "--remote-webserver=%(remote_webserver)s", "--test-manifest=%(test_manifest)s",
        "--xre-path=%(xre_path)s", "--symbols-path=%(symbols_path)s", "--busybox=%(busybox)s",
        "--total-chunks=%(total_chunks)s", "--this-chunk=%(this_chunk)s",
    ],

    "reftest_options": [
        "--adbpath=%(adbpath)s", "--b2gpath=%(b2gpath)s", "--emulator=%(emulator)s",
        "--emulator-res=800x1000", "--logcat-dir=%(logcat_dir)s",
        "--remote-webserver=%(remote_webserver)s", "--ignore-window-size",
        "--xre-path=%(xre_path)s", "--symbols-path=%(symbols_path)s", "--busybox=%(busybox)s",
        "--total-chunks=%(total_chunks)s", "--this-chunk=%(this_chunk)s",
        "%(test_manifest)s",
    ],

    "crashtest_options": [
        "--adbpath=%(adbpath)s", "--b2gpath=%(b2gpath)s", "--emulator=%(emulator)s",
        "--emulator-res=800x1000", "--logcat-dir=%(logcat_dir)s",
        "--remote-webserver=%(remote_webserver)s", "--ignore-window-size",
        "--xre-path=%(xre_path)s", "--symbols-path=%(symbols_path)s", "--busybox=%(busybox)s",
        "--total-chunks=%(total_chunks)s", "--this-chunk=%(this_chunk)s",
        "%(test_manifest)s",
    ],

    "xpcshell_options": [
        "--adbpath=%(adbpath)s", "--b2gpath=%(b2gpath)s", "--emulator=%(emulator)s",
        "--logcat-dir=%(logcat_dir)s", "--manifest=%(test_manifest)s",
        "--testing-modules-dir=%(modules_dir)s", "--symbols-path=%(symbols_path)s",
        "--busybox=%(busybox)s", "--total-chunks=%(total_chunks)s", "--this-chunk=%(this_chunk)s",
    ],
}
