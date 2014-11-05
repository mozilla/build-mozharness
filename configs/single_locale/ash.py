config = {
    "nightly_build": True,
    "branch": "ash",
    "en_us_binary_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/ash-%(platform)s/latest/",
    "update_channel": "nightly",

    # l10n
    "hg_l10n_base": "https://hg.mozilla.org/l10n-central",

    # mar
    "enable_partials": True,
    "mar_tools_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/ash-%(platform)s/latest/",
    "previous_mar_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central-l10n",
    "current_mar_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central",

    # repositories
    "mozilla_dir": "ash",
    "repos": [{
        "vcs": "hg",
        "repo": "https://hg.mozilla.org/projects/ash",
        "revision": "default",
        "dest": "ash",
    }, {
        "vcs": "hg",
        "repo": "https://hg.mozilla.org/build/tools",
        "revision": "default",
        "dest": "tools",
    }, {
        "vcs": "hg",
        "repo": "https://hg.mozilla.org/build/compare-locales",
        "revision": "RELEASE_AUTOMATION"
    }],

}
