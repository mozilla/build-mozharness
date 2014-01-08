BRANCH = "mozilla-aurora"
MOZ_UPDATE_CHANNEL = "aurora"
MOZILLA_DIR = BRANCH
JAVA_HOME = "/tools/jdk6"
OBJDIR = "obj-l10n"
EN_US_BINARY_URL = "http://stage.mozilla.org/pub/mozilla.org/mobile/nightly/latest-%s-android/en-US" % (BRANCH)
#STAGE_SERVER = "dev-stage01.srv.releng.scl3.mozilla.com"
STAGE_SERVER = "stage.mozilla.org"
STAGE_USER = "ffxbld"
STAGE_SSH_KEY = "~/.ssh/ffxbld_dsa"
#AUS_SERVER = "dev-stage01.srv.releng.scl3.mozilla.com"
AUS_SERVER = "aus3-staging.mozilla.org"
AUS_USER = "ffxbld"
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
    "clobberer_url": "http://clobberer.pvt.build.mozilla.org/index.php",
    "locales_file": "%s/mobile/android/locales/all-locales" % MOZILLA_DIR,
    "locales_dir": "mobile/android/locales",
    "ignore_locales": ["en-US"],
    "tooltool_config": {
        "manifest": "mobile/android/config/tooltool-manifests/android/releng.manifest",
        "output_dir": "%(abs_work_dir)s/" + MOZILLA_DIR,
        "bootstrap_cmd": ["bash", "-xe", "setup.sh"],
    },
    "exes": {
        'tooltool.py': '/tools/tooltool.py',
    },
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],
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
        # so ugly, bug 951238
        "LD_LIBRARY_PATH": "/lib:/tools/gcc-4.7.2-0moz1/lib:/tools/gcc-4.7.2-0moz1/lib64",
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
    "mock_target": "mozilla-centos6-x86_64",
    "mock_packages": ['autoconf213', 'python', 'zip', 'mozilla-python27-mercurial', 'git', 'ccache',
                      'glibc-static', 'libstdc++-static', 'perl-Test-Simple', 'perl-Config-General',
                      'gtk2-devel', 'libnotify-devel', 'yasm',
                      'alsa-lib-devel', 'libcurl-devel',
                      'wireless-tools-devel', 'libX11-devel',
                      'libXt-devel', 'mesa-libGL-devel',
                      'gnome-vfs2-devel', 'GConf2-devel', 'wget',
                      'mpfr',  # required for system compiler
                      'xorg-x11-font*',  # fonts required for PGO
                      'imake',  # required for makedepend!?!
                      'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1', 'yasm', 'ccache',  # <-- from releng repo
                      'valgrind', 'dbus-x11',
                      'pulseaudio-libs-devel',
                      'gstreamer-devel', 'gstreamer-plugins-base-devel',
                      'freetype-2.3.11-6.el6_1.8.x86_64',
                      'freetype-devel-2.3.11-6.el6_1.8.x86_64',
                      'java-1.6.0-openjdk-devel',
                      'openssh-clients',
                      'zlib-devel-1.2.3-27.el6.i686',
                      ],
    "mock_files": [
        ("/home/cltbld/.ssh", "/home/mock_mozilla/.ssh"),
    ],
}
