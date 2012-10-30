# This is a template config file for b2g emulator unittest testing

config = {
    # mozharness script options
    "application": "b2g",
    "test_suite": "reftest",                                # reftest or mochitest

    "emulator_url": "http://127.0.1.1/b2g/emulator.zip",    # url to emulator zip file
    "installer_url": "http://127.0.1.1/b2g/b2g.tar.gz",     # url to gecko build
    "xpcshell_url": "http://127.0.1.1/b2g/xpcshell.zip",    # url to xpcshell zip file
    "test_url": "http://127.0.1.1/b2g/tests.zip",           # url to tests.zip

    # testsuite options
    #"adb_path": "path/to/adb",           # defaults - os.environ['ADB_PATH']
    #"test_manifest": "path/to/manifest", # defaults - mochitest: "b2g.json"
                                          #              reftest: "tests/layout/reftests/reftest.list"
    "total_chunks": 8,
    "this_chunk": 1,
}
