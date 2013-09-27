# This is a template config file for b2g emulator unittest testing

config = {
    # mozharness script options
    "application": "b2g",
    "test_suite": "mochitest",                               # reftest, mochitest or xpcshell
    "gaia_repo": "http://hg.mozilla.org/integration/gaia-central",

    "installer_url": "http://ftp.mozilla.org/pub/mozilla.org/b2g/tinderbox-builds/mozilla-central-linux64_gecko/1380197683/en-US/b2g-27.0a1.en-US.linux-x86_64.tar.bz2",
    "xre_url": "http://localhost/xre.zip",
    "xre_path": "xulrunner-sdk",
    "test_url": "http://localhost/tests.zip",

    # testsuite options
    "run_file_names": {
        "mochitest": "runtestsb2g.py",
    },
    "mochitest_options": [
        "--console-level=INFO", "--test-manifest=%(test_manifest)s",
        "--total-chunks=%(total_chunks)s", "--this-chunk=%(this_chunk)s",
        "--profile=%(gaia_profile)s", "--app=%(application)s", "--desktop",
        "--utility-path=%(utility_path)s", "--xre-path=%(utility_path)s",
        "--certificate-path=%(cert_path)s",
    ],
}
