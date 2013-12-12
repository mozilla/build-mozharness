BRANCH = "mozilla-central"
MOZILLA_DIR = BRANCH
HG_SHARE_BASE_DIR = "/builds/hg-shared"
EN_US_BINARY_URL = "http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central"
OBJDIR = "obj-l10n"
MOZ_UPDATE_CHANNEL = "nightly"
STAGE_SERVER = "dev-stage01.build.sjc1.mozilla.com"
#STAGE_SERVER = "stage.mozilla.org"
STAGE_USER = "ffxbld"
STAGE_SSH_KEY = "~/.ssh/ffxbld_dsa"
AUS_SERVER = "dev-stage01.build.sjc1.mozilla.com"
#AUS_SERVER = "aus2-staging.mozilla.org"
AUS_USER = "ffxbld"
AUS_SSH_KEY = "~/.ssh/ffxbld_dsa"
AUS_UPLOAD_BASE_DIR = "/opt/aus2/incoming/2/Firefox"
AUS_BASE_DIR = BRANCH + "/%(build_target)s/%(buildid)s/%(locale)s"
CANDIDATES_URL = "https://ftp.mozilla.org/pub/mozilla.org/firefox/%s" % MOZ_UPDATE_CHANNEL
PLATFORM = "mac"
config = {
    "mozilla_dir": MOZILLA_DIR,
    "snippet_base_url": "http://example.com",  # fix it
    "mozconfig": "%s/browser/config/mozconfigs/macosx-universal/l10n-mozconfig" % MOZILLA_DIR,
    "src_xulrunner_mozconfig": "xulrunner/config/mozconfigs/macosx64/xulrunner",
    "platform": PLATFORM,
    "binary_url": EN_US_BINARY_URL,
    "repos": [{
        "vcs": "hg",
        "repo": "http://hg.mozilla.org/mozilla-central",
        "revision": "default",
        "dest": MOZILLA_DIR,
    }, {
        "vcs": "hg",
        "repo": "http://hg.mozilla.org/build/tools",
        "revision": "default",
        "dest": "tools",
    }, {
        "vcs": "hg",
        "repo": "http://hg.mozilla.org/build/compare-locales",
        "revision": "RELEASE_AUTOMATION"
    }],
    "repack_env": {
        "MOZ_OBJDIR": OBJDIR,
        "EN_US_BINARY_URL": EN_US_BINARY_URL,
        "MOZ_UPDATE_CHANNEL": MOZ_UPDATE_CHANNEL,
        "MOZ_SYMBOLS_EXTRA_BUILDID": "macosx64",
        "MOZ_PKG_PLATFORM": "mac",
        "IS_NIGHTLY": "yes",
        "DIST": "%(abs_objdir)s",
        "LOCALE_MERGEDIR": "%(abs_merge_dir)s/",
    },
    "log_name": "single_locale",
    "objdir": OBJDIR,
    "js_src_dir": "js/src",
    "make_dirs": ['config'],
    "vcs_share_base": HG_SHARE_BASE_DIR,

    "upload_env": {
        "UPLOAD_USER": STAGE_USER,
        "UPLOAD_SSH_KEY": STAGE_SSH_KEY,
        "UPLOAD_HOST": STAGE_SERVER,
        #"POST_UPLOAD_CMD": "post_upload.py -b mozilla-central-android-l10n -p mobile -i %(buildid)s --release-to-latest --release-to-dated",
        "POST_UPLOAD_CMD": "post_upload.py -b mozilla-central-l10n -p firefox -i %(buildid)s  --release-to-latest --release-to-dated",
        "UPLOAD_TO_TEMP": "1",
    },
    #l10n
    "ignore_locales": ["en-US"],
    "l10n_dir": "l10n",
    "l10n_stage_dir": "dist/firefox/l10n-stage",
    "locales_file": "%s/browser/locales/all-locales" % MOZILLA_DIR,
    "locales_dir": "browser/locales",
    "hg_l10n_base": "http://hg.mozilla.org/l10n-central",
    "hg_l10n_tag": "default",
    "merge_locales": True,
    "clobber_file": 'CLOBBER',


    #MAR
    'previous_mar_url': 'https://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central-l10n',
    "previous_mar_dir": "previous",
    "current_mar_dir": "current",
    "update_mar_dir": "dist/update",  # sure?
    "previous_mar_filename": "previous.mar",
    "current_work_mar_dir": "current.work",
    "package_base_dir": "dist/l10n-stage",
    "application_ini": "Contents/MacOS/application.ini",
    "buildid_section": 'App',
    "buildid_option": "BuildID",
    "unpack_script": "tools/update-packaging/unwrap_full_update.pl",
    "incremental_update_script": "tools/update-packaging/make_incremental_update.sh",
    "update_packaging_dir": "tools/update-packaging",
    "local_mar_tool_dir": "dist/host/bin",
    "mar": "mar",
    "mbsdiff": "mbsdiff",
    "candidates_base_url": CANDIDATES_URL,
    "partials_url": "%(base_url)s/latest-mozilla-central/",
    "mar_tools_url": "https://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/latest-mozilla-central/mar-tools/macosx64/",
    "complete_mar": "firefox-%(version)s.en-US.mac.complete.mar",
    "localized_mar": "firefox-%(version)s.%(locale)s.mac.complete.mar",
    #../update/mac64/de/nightly-27.0a1.complete.mar
    #"partial_mar": "%(platform)s/%(locale)s/firefox-%(version)s.partial.mar",
    #firefox-27.0a1.en-US.mac.partial.20130917030214-20130918030202.mar"
    "partial_mar": "firefox-%(version)s.%(locale)s.partial.%(from_buildid)s-%(to_buildid)s.mar",

    # AUS
    "build_target": "Linux_x86-gcc3",
    "aus_server": AUS_SERVER,
    "aus_user": AUS_USER,
    "aus_ssh_key": AUS_SSH_KEY,
    "aus_upload_base_dir": AUS_UPLOAD_BASE_DIR,
    "aus_base_dir": AUS_BASE_DIR,
}
