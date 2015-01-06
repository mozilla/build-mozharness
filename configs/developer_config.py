"""
This config file can be appended to any other mozharness job
running under treeherder. The purpose of this config is to
override values that are specific to Release Engineering machines
that can reach specific hosts within their network.
In other words, this config allows you to run any job
outside of the Release Engineering network

Using this config file should be accompanied with using
--test-url and --installer-url where appropiate
"""

import os
LOCAL_WORKDIR = os.path.expanduser("~/.mozilla/releng")
TOOLTOOL_SERVER = "https://secure.pub.build.mozilla.org/tooltool/pvt/build"

config = {
    "developer_mode": True,
    "local_workdir": LOCAL_WORKDIR,

    # General variables overwrite
    "exes": {},
    "find_links": ["http://pypi.pub.build.mozilla.org/pub"],
    "replace_urls": [
        ("http://pvtbuilds.pvt.build",
         "https://pvtbuilds"),
        ("http://tooltool.pvt.build.mozilla.org/build",
         TOOLTOOL_SERVER)
    ],

    # Talos related
    "python_webserver": True,
    "virtualenv_path": '%s/build/venv' % os.getcwd(),

    # Tooltool related
    "tooltool_servers": [
        TOOLTOOL_SERVER
    ],
    "tooltool_cache": os.path.join(LOCAL_WORKDIR, "builds/tooltool_cache"),
    "tooltool_py_url": "https://raw.githubusercontent.com/mozilla/" + \
        "build-tooltool/master/tooltool.py",

    # Android related
    "host_utils_url": TOOLTOOL_SERVER + "/sha512/" +\
        "372c89f9dccaf5ee3b9d35fd1cfeb089e1e5db3ff1c04e35aa3adc8800bc61a2" + \
        "ae10e321f37ae7bab20b56e60941f91bb003bcb22035902a73d70872e7bd3282",
}
