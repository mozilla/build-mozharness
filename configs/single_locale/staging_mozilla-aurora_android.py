BRANCH = "mozilla-aurora"
MOZ_UPDATE_CHANNEL = "aurora"
MOZILLA_DIR = BRANCH
JAVA_HOME = "/tools/jdk6"
OBJDIR = "obj-l10n"
EN_US_BINARY_URL = "http://stage.mozilla.org/pub/mozilla.org/mobile/nightly/latest-%s-android/en-US" % (BRANCH)
STAGE_SERVER = "dev-stage01.srv.releng.scl3.mozilla.com"
#STAGE_SERVER = "stage.mozilla.org"
STAGE_USER = "ffxbld"
STAGE_SSH_KEY = "~/.ssh/ffxbld_dsa"
AUS_SERVER = "dev-stage01.srv.releng.scl3.mozilla.com"
#AUS_SERVER = "aus3-staging.mozilla.org"
AUS_USER = "ffxbld"
#AUS_SSH_KEY = "~/.ssh/auspush"
AUS_SSH_KEY = "~/.ssh/ffxbld_dsa"
AUS_UPLOAD_BASE_DIR = "/opt/aus2/incoming/2/Fennec"
AUS_BASE_DIR = BRANCH + "/%(build_target)s/%(buildid)s/%(locale)s"
HG_SHARE_BASE_DIR = "/builds/hg-shared"

config = {
    "log_name": "single_locale",
    "objdir": OBJDIR,
    "is_automation": True,
    "buildbot_json_path": "buildprops.json",
    "purge_minsize": 10,
    "force_clobber": True,
    "clobberer_url": "http://clobberer-stage.pvt.build.mozilla.org/index.php",
    "locales_file": "%s/mobile/android/locales/all-locales" % MOZILLA_DIR,
    "locales_dir": "mobile/android/locales",
    "ignore_locales": ["en-US"],
    "repos": [{
        "repo": "http://hg.mozilla.org/releases/mozilla-aurora",
        "revision": "default",
        "dest": MOZILLA_DIR,
    }, {
        "repo": "http://hg.mozilla.org/build/buildbot-configs",
        "revision": "default",
        "dest": "buildbot-configs"
    }, {
        "repo": "http://hg.mozilla.org/build/tools",
        "revision": "default",
        "dest": "tools"
    }, {
        "repo": "http://hg.mozilla.org/build/compare-locales",
        "revision": "RELEASE_AUTOMATION"
    }],
    "hg_l10n_base": "http://hg.mozilla.org/releases/l10n/%s" % BRANCH,
    "hg_l10n_tag": "default",
    'vcs_share_base': HG_SHARE_BASE_DIR,

    "l10n_dir": MOZILLA_DIR,
    "repack_env": {
        "JAVA_HOME": JAVA_HOME,
        "PATH": JAVA_HOME + "/bin:%(PATH)s",
        "MOZ_OBJDIR": OBJDIR,
        "EN_US_BINARY_URL": EN_US_BINARY_URL,
        "LOCALE_MERGEDIR": "%(abs_merge_dir)s/",
        "MOZ_UPDATE_CHANNEL": MOZ_UPDATE_CHANNEL,
    },
    # TODO ideally we could get this info from a central location.
    # However, the agility of these individual config files might trump that.
    "upload_env": {
        "UPLOAD_USER": STAGE_USER,
        "UPLOAD_SSH_KEY": STAGE_SSH_KEY,
        "UPLOAD_HOST": STAGE_SERVER,
        "POST_UPLOAD_CMD": "post_upload.py -b mozilla-aurora-android-l10n -p mobile -i %(buildid)s --release-to-latest --release-to-dated",
        "UPLOAD_TO_TEMP": "1",
    },
    "merge_locales": True,
    "make_dirs": ['config'],
    "mozilla_dir": MOZILLA_DIR,
    "mozconfig": "%s/mobile/android/config/mozconfigs/android/l10n-nightly" % MOZILLA_DIR,
    "signature_verification_script": "tools/release/signing/verify-android-signature.sh",

    # AUS
    "build_target": "Android_arm-eabi-gcc3",
    "aus_server": AUS_SERVER,
    "aus_user": AUS_USER,
    "aus_ssh_key": AUS_SSH_KEY,
    "aus_upload_base_dir": AUS_UPLOAD_BASE_DIR,
    "aus_base_dir": AUS_BASE_DIR,

    # Mock
    "mock_target": "mozilla-centos6-i386",
    "mock_packages": [
        "autoconf213", "mozilla-python27-mercurial", "ccache",
        "android-sdk15", "android-sdk16", "android-ndk5", "android-ndk8",
        "zip", "java-1.6.0-openjdk-devel", "zlib-devel", "glibc-static",
        "openssh-clients", "mpfr", "wget",
    ],
    "mock_files": [
        ("/home/cltbld/.ssh", "/home/mock_mozilla/.ssh"),
    ],
}
