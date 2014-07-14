# This is a template config file for marionette production.
import os
import platform

HG_SHARE_BASE_DIR = "/builds/hg-shared"

if platform.system().lower() == 'darwin':
    xre_url = "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/441be719e6984d24e9eadca5d13a1cd7d22e81505b21a82d25a7da079a48211b5feb4525a6f32100a00748f8a824a341065d66a97be8e932c3a3e1e55ade0ede"
else:
    xre_url = "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/b48e7defed365b5899f4a782304e4c621e94c6759e32fdec66aa3e088688401e4c404b1778cd0c6b947d9faa874f60a68e1c7d8ccaa5f2d25077eafad5d533cc"

config = {
    # marionette options
    "test_type": "b2g",
    "marionette_address": "localhost:2828",
    "gaiatest": True,
    "xre_url": xre_url,
    "application": "b2g",

    "vcs_share_base": HG_SHARE_BASE_DIR,
    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },

    "find_links": [
        "http://pypi.pvt.build.mozilla.org/pub",
        "http://pypi.pub.build.mozilla.org/pub",
    ],
    "pip_index": False,

    "buildbot_json_path": "buildprops.json",

    "default_actions": [
        'clobber',
        'read-buildbot-config',
        'pull',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-marionette',
    ],
    "download_symbols": "ondemand",
    "download_minidump_stackwalk": True,
    "default_blob_upload_servers": [
        "https://blobupload.elasticbeanstalk.com",
    ],
    "blob_uploader_auth_file": os.path.join(os.getcwd(), "oauth.txt"),
    "vcs_output_timeout": 1760,
    "in_tree_config": "config/mozharness/marionette.py",
}
