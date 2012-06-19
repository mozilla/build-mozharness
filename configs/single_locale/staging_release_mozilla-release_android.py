BRANCH = "mozilla-release"
MOZ_UPDATE_CHANNEL = "release"
MOZILLA_DIR = BRANCH
JAVA_HOME = "/tools/jdk6"
JARSIGNER = "tools/release/signing/mozpass.py"
OBJDIR = "obj-l10n"
STAGE_SERVER = "dev-stage01.srv.releng.scl3.mozilla.com"
EN_US_BINARY_URL = "http://" + STAGE_SERVER + "/pub/mozilla.org/mobile/candidates/%(version)s-candidates/build%(buildnum)d/unsigned/android/en-US"
STAGE_USER = "ffxbld"
STAGE_SSH_KEY = "~/.ssh/ffxbld_dsa"
HG_SHARE_BASE_DIR = "/builds/hg-shared"

config = {
    "log_name": "single_locale",
    "objdir": OBJDIR,
    "locales_file": "buildbot-configs/mozilla/l10n-changesets_mobile-release.json",
    "locales_dir": "mobile/android/locales",
    "locales_platform": "android",
    "ignore_locales": ["en-US"],
    "repos": [{
        "repo": "http://hg.mozilla.org/%(user_repo_override)s/mozilla-release",
        "revision": "default",
        "dest": MOZILLA_DIR,
    },{
        "repo": "http://hg.mozilla.org/%(user_repo_override)s/buildbot-configs",
        "revision": "default",
        "dest": "buildbot-configs"
    },{
        "repo": "http://hg.mozilla.org/%(user_repo_override)s/tools",
        "revision": "default",
        "dest": "tools"
    },{
        "repo": "http://hg.mozilla.org/%(user_repo_override)s/compare-locales",
        "revision": "RELEASE_AUTOMATION"
    }],
    "hg_l10n_base": "http://hg.mozilla.org/%(user_repo_override)s/",
    "hg_l10n_tag": "default",
    'vcs_share_base': HG_SHARE_BASE_DIR,
    "l10n_dir": MOZILLA_DIR,

    "release_config_file": "buildbot-configs/mozilla/staging_release-fennec-mozilla-release.py",
    "repack_env": {
        "JAVA_HOME": JAVA_HOME,
        "PATH": JAVA_HOME + "/bin:%(PATH)s",
        "MOZ_PKG_VERSION": "%(version)s",
        "MOZ_OBJDIR": OBJDIR,
        "JARSIGNER": "%(abs_work_dir)s/" + JARSIGNER,
        "LOCALE_MERGEDIR": "%(abs_merge_dir)s/",
        "MOZ_UPDATE_CHANNEL": MOZ_UPDATE_CHANNEL,
    },
    "base_en_us_binary_url": EN_US_BINARY_URL,
    # TODO ideally we could get this info from a central location.
    # However, the agility of these individual config files might trump that.
    "upload_env": {
        "UPLOAD_USER": STAGE_USER,
        "UPLOAD_SSH_KEY": STAGE_SSH_KEY,
        "UPLOAD_HOST": STAGE_SERVER,
        "UPLOAD_TO_TEMP": "1",
        "MOZ_PKG_VERSION": "%(version)s",
    },
    "base_post_upload_cmd": "post_upload.py -p mobile -n %(buildnum)s -v %(version)s --builddir android/%(locale)s --release-to-mobile-candidates-dir --nightly-dir=candidates",
    "merge_locales": True,
    "make_dirs": ['config'],
    "mozilla_dir": MOZILLA_DIR,
    "mozconfig": "%s/mobile/android/config/mozconfigs/android/l10n-release" % MOZILLA_DIR,
    "jarsigner": JARSIGNER,
    "signature_verification_script": "tools/release/signing/verify-android-signature.sh",
    "default_actions": [
        "clobber",
        "pull",
        "list-locales",
        "setup",
        "repack",
        "upload-repacks",
    ],
}
