import os
import sys

STAGE_PRODUCT = 'firefox'
STAGE_USERNAME = 'ffxbld'
STAGE_SSH_KEY = 'ffxbld_dsa'

config = {
    #########################################################################
    ######## WINDOWS GENERIC CONFIG KEYS/VAlUES
    # if you are updating this with custom 32 bit keys/values please add them
    # below under the '32 bit specific' code block otherwise, update in this
    # code block and also make sure this is synced with
    # releng_base_linux_64_builds.py

    'default_actions': [
        'clobber',
        'clone-tools',
        # 'setup-mock', windows do not use mock
        'build',
        'generate-build-props',
        # 'generate-build-stats',
        'symbols',
        'packages',
        'upload',
        'sendchanges',
        'pretty-names',
        'check-l10n',
        'check-test',
        'update',  # decided by query_is_nightly()
        # 'ccache-stats',
    ],
    "buildbot_json_path": "buildprops.json",
    'exes': {
        'python': sys.executable,
        'hgtool.py': [
            sys.executable,
            os.path.join(
                os.getcwd(), 'build', 'tools', 'buildfarm', 'utils', 'hgtool.py'
            )
        ],
        "buildbot": "/tools/buildbot/bin/buildbot",
        "make": [
            sys.executable,
            os.path.join(
                os.getcwd(), 'build', 'source', 'build', 'pymake', 'make.py'
            )
        ]
    },
    'app_ini_path': '%(obj_dir)s/dist/bin/application.ini',
    # decides whether we want to use moz_sign_cmd in env
    'enable_signing': True,
    'purge_skip': ['info', 'rel-*:45d', 'tb-rel-*:45d'],
    'purge_basedirs':  [],
    'enable_ccache': False,
    'vcs_share_base': 'C:/builds/hg-shared',
    'objdir': 'obj-firefox',
    'tooltool_script': [sys.executable,
                        'C:/mozilla-build/tooltool.py'],
    'tooltool_bootstrap': "setup.sh",
    # only linux counts ctors
    'enable_count_ctors': False,
    'package_targets': ['package', 'package-tests', 'installer'],
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
    # TODO -- nightly
#     'update_env': {
#         'MAR': '../dist/host/bin/mar',
#         'MBSDIFF': '../dist/host/bin/mbsdiff'
#     },
    # TODO -- nightly
#     'latest_mar_dir': '/pub/mozilla.org/%s/nightly/latest-%%(branch)s' % (
#         STAGE_PRODUCT,),
#     #########################################################################
#
#
#     #########################################################################
#     ###### 32 bit specific ######
    'platform': 'win32',
    'stage_platform': 'win32',
    # TODO -- nightly
#     'platform_ftp_name': '',
#     'update_platform': '',
    'enable_max_vsize': True,
    'env': {
        'BINSCOPE': 'C:/Program Files (x86)/Microsoft/SDL BinScope/BinScope.exe',
        'HG_SHARE_BASE_DIR': 'C:/builds/hg-shared',
        'MOZ_CRASHREPORTER_NO_REPORT': '1',
        'MOZ_OBJDIR': 'obj-firefox',
        'PATH': 'C:/mozilla-build/nsis-2.46u;C:/mozilla-build/python27;'
                'C:/mozilla-build/buildbotve/scripts;'
                '%s' % (os.environ.get('path')),
        'PDBSTR_PATH': '/c/Program Files (x86)/Windows Kits/8.0/Debuggers/x64/srcsrv/pdbstr.exe',
        'POST_SYMBOL_UPLOAD_CMD': '/usr/local/bin/post-symbol-upload.py',
        'PROPERTIES_FILE': os.path.join(os.getcwd(), 'buildprops.json'),
        'SYMBOL_SERVER_HOST': 'symbolpush.mozilla.org',
        'SYMBOL_SERVER_PATH': '/mnt/netapp/breakpad/symbols_ffx/',
        'SYMBOL_SERVER_SSH_KEY': '/c/Users/cltbld/.ssh/ffxbld_dsa',
        'SYMBOL_SERVER_USER': 'ffxbld',
        'TINDERBOX_OUTPUT': '1'
    },
    'purge_minsize': 12,
    'src_mozconfig': 'browser/config/mozconfigs/win32/nightly',
    'tooltool_manifest_src': "browser/config/tooltool-manifests/win32/releng.manifest",
    'package_filename': '*.win32.zip',

    "check_test_env": {
        'MINIDUMP_STACKWALK': '%(abs_tools_dir)s/breakpad/win32/minidump_stackwalk.exe',
        'MINIDUMP_SAVE_PATH': '%(base_work_dir)s/minidumps',
    },
    #########################################################################
}
