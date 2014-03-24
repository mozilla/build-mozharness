STAGE_PRODUCT = 'firefox'
# TODO Reminder, stage_username and stage_ssh_key differ on Try
STAGE_USERNAME = 'ffxbld'
STAGE_SSH_KEY = 'ffxbld_dsa'

config = {
    #########################################################################
    ######## LINUX GENERIC CONFIG KEYS/VAlUES
    # if you are updating this with custom 64 bit keys/values please add them
    # below under the '64 bit specific' code block otherwise, update in this
    # code block and also make sure this is synced with
    # releng_base_linux_64_builds.py

    'app_ini_path': '%(obj_dir)s/dist/bin/application.ini',
    # decides whether we want to use moz_sign_cmd in env
    'enable_signing': True,
    "buildbot_json_path": "buildprops.json",
    'default_actions': [
        'clobber',
        'pull',
        'setup-mock',
        'build',
        'generate-build-props',
        'generate-build-stats',
        'symbols',
        'packages',
        'upload',
        'sendchanges',
        'pretty-names',
        'check-l10n',
        'check-test',
        'update',  # decided by query_is_nightly()
        'enable-ccache',
    ],
    'exes': {
        "buildbot": "/tools/buildbot/bin/buildbot",
    },
    'purge_skip': ['info', 'rel-*:45d', 'tb-rel-*:45d'],
    'purge_basedirs':  ["/mock/users/cltbld/home/cltbld/build"],
    # mock shtuff
    'use_mock':  True,
    'mock_mozilla_dir':  '/builds/mock_mozilla',
    'mock_target': 'mozilla-centos6-x86_64',
    'mock_files': [
        ('/home/cltbld/.ssh', '/home/mock_mozilla/.ssh'),
        ('/home/cltbld/.hgrc', '/builds/.hgrc'),
        ('/builds/gapi.data', '/builds/gapi.data'),
        ('/tools/tooltool.py', '/builds/tooltool.py'),
    ],
    'enable_ccache': True,
    'ccache_env': {
        'CCACHE_BASEDIR': "%(base_dir)s",
        'CCACHE_COMPRESS': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_HASHDIR': '',
        'CCACHE_UMASK': '002',
    },
    'vcs_share_base': '/builds/hg-shared',
    'objdir': 'obj-firefox',
    'old_packages': [
        "%(objdir)s/dist/firefox-*",
        "%(objdir)s/dist/fennec*",
        "%(objdir)s/dist/seamonkey*",
        "%(objdir)s/dist/thunderbird*",
        "%(objdir)s/dist/install/sea/*.exe"
    ],
    'tooltool_script': "/tools/tooltool.py",
    'tooltool_bootstrap': "setup.sh",
    # in linux we count ctors
    'enable_count_ctors': True,
    'enable_package_tests': True,
    'stage_product': STAGE_PRODUCT,
    "enable_talos_sendchange": True,
    "do_pretty_name_l10n_check": True,
    'upload_symbols': True,

    'stage_username': STAGE_USERNAME,
    'stage_ssh_key': STAGE_SSH_KEY,
    'upload_env': {
        # stage_server is dictated from build_pool_specifics.py
        'UPLOAD_HOST': "%(stage_server)s",
        'UPLOAD_USER': STAGE_USERNAME,
        'UPLOAD_TO_TEMP': '1',
        'UPLOAD_SSH_KEY': '~/.ssh/%s' % (STAGE_SSH_KEY,),
    },
    'update_env': {
        'MAR': '../dist/host/bin/mar',
        'MBSDIFF': '../dist/host/bin/mbsdiff'
    },
    'latest_mar_dir': '/pub/mozilla.org/%s/nightly/latest-%%(branch)s' % (
        STAGE_PRODUCT,),
    #########################################################################


    #########################################################################
    ###### 64 bit specific ######
    # TODO we may need to add these other platform keys but thus far, I don't
    'platform': 'linux64',
    # # this will change for sub configs like asan, pgo etc
    # 'platform_variation': '',
    # 'complete_platform': 'linux',
    # 'stage_platform': 'linux64',
    'platform_ftp_name': 'linux-x86_64.complete.mar',
    'env': {
        'DISPLAY': ':2',
        'HG_SHARE_BASE_DIR': '/builds/hg-shared',
        'MOZ_OBJDIR': 'obj-firefox',
        # SYMBOL_SERVER_HOST is dictated from build_pool_specifics.py
        'SYMBOL_SERVER_HOST': "%(symbol_server_host)s",
        'SYMBOL_SERVER_USER': 'ffxbld',
        'SYMBOL_SERVER_PATH': '/mnt/netapp/breakpad/symbols_ffx/',
        'POST_SYMBOL_UPLOAD_CMD': '/usr/local/bin/post-symbol-upload.py',
        'SYMBOL_SERVER_SSH_KEY': "/home/mock_mozilla/.ssh/ffxbld_dsa",
        'TINDERBOX_OUTPUT': '1',
        'MOZ_CRASHREPORTER_NO_REPORT': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_COMPRESS': '1',
        'CCACHE_UMASK': '002',
        'LC_ALL': 'C',
        ## 64 bit specific
        'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib64/ccache:/bin:\
/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:\
/tools/python27-mercurial/bin:/home/cltbld/bin',
        'LD_LIBRARY_PATH': "/tools/gcc-4.3.3/installed/lib64",
        ##
    },
    'purge_minsize': 14,
    'mock_packages': [
        'autoconf213', 'python', 'zip', 'mozilla-python27-mercurial',
        'git', 'ccache', 'perl-Test-Simple', 'perl-Config-General',
        'yasm', 'wget',
        'mpfr',  # required for system compiler
        'xorg-x11-font*',  # fonts required for PGO
        'imake',  # required for makedepend!?!
        ### <-- from releng repo
        'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
        'yasm', 'ccache',
        ###
        'valgrind', 'dbus-x11',
        ######## 64 bit specific ###########
        'glibc-static', 'libstdc++-static',
        'gtk2-devel', 'libnotify-devel',
        'alsa-lib-devel', 'libcurl-devel', 'wireless-tools-devel',
        'libX11-devel', 'libXt-devel', 'mesa-libGL-devel', 'gnome-vfs2-devel',
        'GConf2-devel',
        ### from releng repo
        'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
        'yasm', 'ccache',
        ###
        'pulseaudio-libs-devel', 'gstreamer-devel',
        'gstreamer-plugins-base-devel', 'freetype-2.3.11-6.el6_1.8.x86_64',
        'freetype-devel-2.3.11-6.el6_1.8.x86_64'
    ],
    'src_mozconfig': 'browser/config/mozconfigs/linux64/nightly',
    'tooltool_manifest_src': "browser/config/tooltool-manifests/linux64/\
releng.manifest",
    'package_filename': '*.linux-x86_64*.tar.bz2',
    "check_test_env": {
        'MINIDUMP_STACKWALK': 'breakpad/linux64/minidump_stackwalk',
        'MINIDUMP_SAVE_PATH': 'minidumps',
    },
    'base_name': 'Linux_x86-64_%(branch)s',
    'update_platform': 'Linux_x86_64-gcc3',
    'use_platform_in_symbols_extra_buildid': True,
    #########################################################################
}
