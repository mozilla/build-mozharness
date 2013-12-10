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
        "target_push_url": "ssh://hg.mozilla.org/integration/b2g-inbound",
        "target_pull_url": "https://hg.mozilla.org/integration/b2g-inbound",
        "target_tag": "default",
        "target_repo_name": "b2g-inbound",
    }, {
        "polling_url": "https://hg.mozilla.org/integration/gaia-1_2/json-pushes?full=1",
        "branch": "default",
        "repo_url": "https://hg.mozilla.org/integration/gaia-1_2",
        "repo_name": "gaia-1_2",
        "target_push_url": "ssh://hg.mozilla.org/releases/mozilla-b2g26_v1_2",
        "target_pull_url": "https://hg.mozilla.org/releases/mozilla-b2g26_v1_2",
        "target_tag": "default",
        "target_repo_name": "mozilla-b2g26_v1_2",
    }, {
        "polling_url": "https://hg.mozilla.org/integration/gaia-1_2f/json-pushes?full=1",
        "branch": "default",
        "repo_url": "https://hg.mozilla.org/integration/gaia-1_2f",
        "repo_name": "gaia-1_2f",
        "target_push_url": "ssh://hg.mozilla.org/releases/mozilla-b2g26_v1_2f",
        "target_pull_url": "https://hg.mozilla.org/releases/mozilla-b2g26_v1_2f",
        "target_tag": "default",
        "target_repo_name": "mozilla-b2g26_v1_2f",
    }, {
        "polling_url": "https://hg.mozilla.org/integration/gaia-1_3/json-pushes?full=1",
        "branch": "default",
        "repo_url": "https://hg.mozilla.org/integration/gaia-1_3",
        "repo_name": "gaia-1_3",
        "target_push_url": "ssh://hg.mozilla.org/releases/mozilla-aurora",
        "target_pull_url": "https://hg.mozilla.org/releases/mozilla-aurora",
        "target_tag": "default",
        "target_repo_name": "mozilla-aurora",
    }],
}
