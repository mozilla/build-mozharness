#!/usr/bin/env python
config = {
    "exes": {
        # Get around the https warnings
        "hg": ['/usr/local/bin/hg', "--config", "web.cacerts=/etc/pki/tls/certs/ca-bundle.crt"],
        "hgtool.py": ["/usr/local/bin/hgtool.py"],
        "gittool.py": ["/usr/local/bin/gittool.py"],
    },
    'gecko_pull_url': 'https://hg.mozilla.org/releases/mozilla-b2g28_v1_3t',
    'gecko_push_url': 'ssh://hg.mozilla.org/releases/mozilla-b2g28_v1_3t',
    'gecko_local_dir': 'mozilla-b2g28_v1_3t',

    'manifests_repo': 'https://git.mozilla.org/b2g/b2g-manifest.git',
    'manifests_revision': 'origin/v1.3t',

    'hg_user': 'B2G Bumper Bot <release+b2gbumper@mozilla.com>',
    "ssh_key": "~/.ssh/ffxbld_dsa",
    "ssh_user": "ffxbld",

    'hgtool_base_bundle_urls': ['https://ftp-ssl.mozilla.org/pub/mozilla.org/firefox/bundles'],

    'skip_gaia_json': True,

    'devices': {
        'tarako': {
            'ignore_projects': ['gecko'],
            'ignore_groups': ['darwin'],
        },
    },
    'repo_remote_mappings': {
        'https://android.googlesource.com/': 'https://git.mozilla.org/external/aosp',
        'git://codeaurora.org/': 'https://git.mozilla.org/external/caf',
        'git://github.com/mozilla-b2g/': 'https://git.mozilla.org/b2g',
        'git://github.com/mozilla/': 'https://git.mozilla.org/b2g',
        'https://git.mozilla.org/releases': 'https://git.mozilla.org/releases',
        'http://android.git.linaro.org/git-ro/': 'https://git.mozilla.org/external/linaro',
        'git://github.com/apitrace/': 'https://git.mozilla.org/external/apitrace',
        # Some mappings to ourself, we want to leave these as-is!
        'https://git.mozilla.org/external/aosp': 'https://git.mozilla.org/external/aosp',
        'https://git.mozilla.org/external/caf': 'https://git.mozilla.org/external/caf',
        'https://git.mozilla.org/b2g': 'https://git.mozilla.org/b2g',
        'https://git.mozilla.org/external/apitrace': 'https://git.mozilla.org/external/apitrace',
        'http://sprdsource.spreadtrum.com:8085/b2g/android': 'https://git.mozilla.org/external/sprd-aosp',
        'http://sprdsource.spreadtrum.com:8085/b2g': 'https://git.mozilla.org/external/sprd-b2g',
    },
}
