VERSION = "7.0b6"
BUILDNUM = 1

config = {
    "log_name": "signdebs",
    "locales_file": "buildbot-configs/mozilla/l10n-changesets_mobile-beta.json",
    "locales": ['en-US', 'multi'],
    "hg_repos": [],
    "package_name": "fennec",
    "repo_name": "%(locale)s",
    "remote_repo_path": "/home/ftp/pub/mozilla.org/mobile/candidates/%s-candidates/repos" % VERSION,
    "remote_user": "ffxbld",
    "remote_ssh_key": "/home/cltbld/.ssh/ffxbld_dsa",
    "remote_host": "stage.mozilla.org",
    "section": "release",
    "sbox_path": "/scratchbox/moz_scratchbox",
    "repo_dir": "repos",
    "base_repo_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%s-candidates/repos" % VERSION,
    "platform_config": {
        "fremantle": {
            "long_catalog_name": "Release Fremantle",
            "short_catalog_name": "fennec",
            "install_file": "%(locale)s_fremantle.install",
            "deb_name_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%s-candidates/build%d/maemo5-gtk/en-US/deb_name.txt" % (VERSION, BUILDNUM),
            "multi_dir_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%s-candidates/build%d/maemo5-gtk/multi" % (VERSION, BUILDNUM),
            "en_us_dir_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%s-candidates/build%d/maemo5-gtk/en-US" % (VERSION, BUILDNUM),
            "l10n_dir_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%s-candidates/build%d/maemo5-gtk" % (VERSION, BUILDNUM),
        }
    }
}
