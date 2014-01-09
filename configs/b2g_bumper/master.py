#!/usr/bin/env python
config = {
    'gecko_pull_url': 'https://hg.mozilla.org/projects/cedar',
    'gecko_push_url': 'ssh://hg.mozilla.org/projects/cedar',
    'gecko_local_dir': 'cedar',

    'manifests_repo': 'https://git.mozilla.org/b2g/b2g-manifest.git',
    'manifests_revision': 'origin/master',

    'hg_user': 'B2G Bumper Bot <release+b2gbumper@mozilla.com>',
    "ssh_key": "~/.ssh/ffxbld_dsa",
    "ssh_user": "ffxbld",

    'hgtool_base_bundle_urls': ['http://ftp.mozilla.org/pub/mozilla.org/firefox/bundles'],

    'gaia_repo_url': 'https://hg.mozilla.org/integration/gaia-central',
    'gaia_revision_file': 'b2g/config/gaia.json',
    'gaia_max_revisions': 5,

    'devices': {
        'emulator-jb': {
            'ignore_projects': ['gecko'],
            'filter_groups': ['darwin'],
        },
        'emulator-ics': {
            'ignore_projects': ['gecko'],
            'filter_groups': ['darwin'],
            'manifest_file': 'emulator.xml',
        },
        'hamachi': {
            'ignore_projects': ['gecko'],
            'filter_groups': ['darwin'],
        },
        'helix': {
            'ignore_projects': ['gecko'],
            'filter_groups': ['darwin'],
        },
        'leo': {
            'ignore_projects': ['gecko'],
            'filter_groups': ['darwin'],
        },
        'mako': {
            'ignore_projects': ['gecko'],
            'filter_groups': ['darwin'],
            'manifest_file': 'nexus-4.xml',
        },
        'inari': {
            'ignore_projects': ['gecko'],
            'filter_groups': ['darwin'],
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
    },
}
