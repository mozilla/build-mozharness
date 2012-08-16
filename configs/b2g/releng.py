#!/usr/bin/env python
import os
config = {
    "ssh_key": os.path.expanduser("~/.ssh/b2gbld_dsa"),
    "ssh_user": "b2gbld",
    "upload_remote_host": "stage.mozilla.org",
    "upload_remote_basepath": "/pub/mozilla.org/b2g/tinderbox-builds",
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],
    "vcs_share_base": "/builds/hg-shared",
    "exes": {
        "tooltool.py": "/tools/tooltool.py",
    },
    "env": {
        "CCACHE_DIR": "/builds/ccache",
        "CCACHE_COMPRESS": "1",
        "CCACHE_UMASK": "002",
    },
}
