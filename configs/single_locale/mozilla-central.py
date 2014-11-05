config = {
    "branch": "mozilla-central",
    "en_us_binary_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central",
    "branch_repo": "https://hg.mozilla.org/mozilla-central",
    "extra_upload_env": {
        "POST_UPLOAD_CMD": "post_upload.py -b %(branch)s-l10n -p firefox -i %(buildid)s --release-to-latest --release-to-dated",
    },

    # l10n
    "hg_l10n_base": "https://hg.mozilla.org/l10n-central",

    # mar
    "enable_partials": True,
    "partials_url": "%(base_url)s/latest-mozilla-central/",
    "mar_tools_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central/mar-tools/linux/",

    # just for testing... (patials/complete mar are not generated on ash)
    "previous_mar_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central-l10n",
    "current_mar_url": "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central",

}
