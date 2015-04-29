# This is a template config file for luciddream production.
import os
import platform

HG_SHARE_BASE_DIR = "/builds/hg-shared"

if platform.system().lower() == 'darwin':
    xre_url = "http://tooltool.pvt.build.mozilla.org/build/sha512/314a6b9e177307950461bf3dd13a92a9ae4ceb35acc865e5bdff58a860f617e7b9bfb9485ab276a0a4ac82b1ea6c9ec60652d2f46dc5a7769c4a5f5d04d6dbcd"
else:
    xre_url = "http://tooltool.pvt.build.mozilla.org/build/sha512/64b655694963a05b9cf8ac7f2e7480898e6613714c9bedafc3236ef633ce76e726585d0a76dbe4b428b5142ce85bebe877b70b5daaecf073e592cb505690839f"

config = {
    # mozharness script options
    "xre_url": xre_url,
    "b2gdesktop_url": "http://ftp.mozilla.org/pub/mozilla.org/b2g/nightly/2015-03-09-00-25-06-mozilla-b2g37_v2_2/b2g-37.0.multi.linux-i686.tar.bz2",

    # mozharness configuration
    "vcs_share_base": HG_SHARE_BASE_DIR,
    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
        'tooltool.py': "/tools/tooltool.py",
        'gittool.py': '%(abs_tools_dir)s/buildfarm/utils/gittool.py',
    },

    "find_links": [
        "http://pypi.pvt.build.mozilla.org/pub",
        "http://pypi.pub.build.mozilla.org/pub",
    ],
    "pip_index": False,

    "buildbot_json_path": "buildprops.json",

    "default_blob_upload_servers": [
        "https://blobupload.elasticbeanstalk.com",
    ],
    "blob_uploader_auth_file": os.path.join(os.getcwd(), "oauth.txt"),
    # will handle in-tree config as subsequent patch
    # "in_tree_config": "config/mozharness/luciddream.py",
    "download_symbols": "ondemand",
    "download_minidump_stackwalk": True,
    "tooltool_servers": ["http://tooltool.pvt.build.mozilla.org/build/"],
    "tooltool_cache": "/builds/tooltool_cache",
}
