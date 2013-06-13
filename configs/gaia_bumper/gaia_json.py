#!/usr/bin/env python

config = {
    "log_name": "gaia_bump",
    "log_to_console": False,
    "log_max_rotate": 99,
    "ssh_key": "~/.ssh/ffxbld_dsa",
    "ssh_user": "ffxbld",
    "hg_user": "Gaia Pushbot <release+gaiajson@mozilla.com>",
    "revision_file": "b2g/config/gaia.json",
    "exes": {
        # Get around the https warnings
        "hg": ['/usr/local/bin/hg', "--config", "web.cacerts=/etc/pki/tls/certs/ca-bundle.crt"],
    },
    "repo_list": [{
        "polling_url": "https://hg.mozilla.org/integration/gaia-central/json-pushes?full=1",
        "branch": "default",
        "repo_url": "https://hg.mozilla.org/integration/gaia-central",
        "repo_name": "gaia-central",
        "target_push_url": "ssh://hg.mozilla.org/projects/birch",
        "target_pull_url": "https://hg.mozilla.org/projects/birch",
        "target_tag": "default",
        "target_repo_name": "birch",
    }],
}
