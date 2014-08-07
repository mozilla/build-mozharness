# This is a template config file for b2g emulator unittest testing
import platform
import os

HG_SHARE_BASE_DIR = "/builds/hg-shared"

if platform.system().lower() == 'darwin':
    xre_url = "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/ce54c2f5abb8b8bae67b129e1218e3c3fe46ed965992987b991d5b401e47db07a894da203978a710ea5498321c3b3d39538db2bca7db230c326af6ff060d7c98"
else:
    xre_url = "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/3287d784370e5459b1bc65781f7dd7aa6ef391a3f20d1ba0754aa5eb0394ea88a4c078ab27157d0011cb028a6a11f3c450a5b3d5d89bf0e0ef7a0bd1069ae319"

config = {
    # mozharness script options
    "xre_url": xre_url,

    # mozharness configuration
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],

    "vcs_share_base": HG_SHARE_BASE_DIR,
    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
        'tooltool.py': "/tools/tooltool.py",
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
        'run-tests',
    ],
    "default_blob_upload_servers": [
        "https://blobupload.elasticbeanstalk.com",
    ],
    "blob_uploader_auth_file": os.path.join(os.getcwd(), "oauth.txt"),
    "vcs_output_timeout": 1760,
}
