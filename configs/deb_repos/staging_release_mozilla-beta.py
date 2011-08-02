VERSION = "6.0b1"
BUILDNUM = 1

config = {
    "log_name": "signdebs",
    "locales_file": "buildbot-configs/mozilla/l10n-changesets_mobile-beta.json",
    "locales": ['en-US', 'multi'],
    "hg_repos": [{
        "repo": "http://hg.mozilla.org/build/buildbot-configs"
    }],
    "package_name": "fennec",
    "repo_name": "%(locale)s",
    "remote_repo_path": "/var/www/html/debtest/%s-candidates" % VERSION,
    "remote_user": "cltbld",
    "remote_ssh_key": "/home/cltbld/.ssh/id_rsa",
    "remote_host": "staging-mobile-master.build.mozilla.org",
    "section": "release",
    "sbox_path": "/scratchbox/moz_scratchbox",
    "repo_dir": "repos.staging",
    "base_repo_url": "http://staging-mobile-master.build.mozilla.org/debtest/%s-candidates" % VERSION,
    "platform_config": {

        "fremantle": {
            "long_catalog_name": "Release Staging Fremantle",
            "short_catalog_name": "fennec",
            "install_file": "%(locale)s_fremantle.install",
            "deb_name_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%s-candidates/build%d/maemo5-gtk/en-US/deb_name.txt" % (VERSION, BUILDNUM),
            "multi_dir_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%s-candidates/build%d/maemo5-gtk/multi" % (VERSION, BUILDNUM),
            "en_us_dir_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%s-candidates/build%d/maemo5-gtk/en-US" % (VERSION, BUILDNUM),
            "l10n_dir_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%s-candidates/build%d/maemo5-gtk" % (VERSION, BUILDNUM)
        }

    }
}
