# This is a template config file for b2g emulator unittest testing
import platform

HG_SHARE_BASE_DIR = "/builds/hg-shared"

if platform.system().lower() == 'darwin':
    xre_url = "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/cb675b8a50a4df7c510d0ba09ddec99950aaa63373f69e69ee86b89755fd04944b140ce02ffdc9faa80e34f53752896a38c91fbab0febc81c583cb80e8515e9e"
else:
    xre_url = "http://runtime-binaries.pvt.build.mozilla.org/tooltool/sha512/d4a0da54e75c27cd2f535e66b586f119ef08b3bde4a9eee03662d296b3434189c542c0a7e7a75954030c04396a9823e22e1f884f5d87c0f4017944cd50ff38de"

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
    "vcs_output_timeout": 1760,
}
