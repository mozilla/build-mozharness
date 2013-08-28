BRANCH = "local-src"
HOME = "/home/sfink"
REPO = HOME + "/src/MI-GC"

config = {
    "hgurl": "http://hg.mozilla.org/",
    "hgtool_base_bundle_urls": ["http://ftp.mozilla.org/pub/mozilla.org/firefox/bundles"],

    "python": "python",
    "sixgill": HOME + "/src/sixgill",
    "sixgill_bin": HOME + "/src/sixgill/bin",

    "repo": REPO,
    "repos": [{
        "repo": REPO,
        "revision": "default",
        "dest": BRANCH,
    }, {
        "repo": "http://hg.mozilla.org/build/tools",
        "revision": "default",
        "dest": "tools"
    }],

    "mock_target": "mozilla-centos6-x86_64",
}
