MOZ_OBJDIR = 'obj-firefox'

config = {
    'default_actions': [
        'clobber',
        'clone-tools',
        'setup-mock',
        'build',
        'generate-build-props',
        # 'generate-build-stats', stat debug skips this action
        # 'symbols', stat debug skips this action
        'packages',
        'upload',
        'sendchanges',
        # 'pretty-names', stat debug skips this action
        # 'check-l10n', stat debug skips this action
        # 'check-test', stat debug skips this action
        'update',  # decided by query_is_nightly()
        'ccache-stats',
    ],
    'debug_build': True,
    'stage_platform': 'linux64-st-an-debug',
    "enable_talos_sendchange": False,  # stat debug doesn't do talos sendchange
    # stat debug doesn't do unittest sendchange or make package-tests
    'package_targets': ['package'],
    'enable_signing': False,
    'purge_minsize': 12,
    'tooltool_manifest_src': "browser/config/tooltool-manifests/linux64/\
clang.manifest",
    'upload_symbols': False,
    "platform_supports_snippets": False,
    "platform_supports_partial": False,
    'platform_supports_post_upload_to_latest': False,

    #### 64 bit build specific #####
    'env': {
        'DISPLAY': ':2',
        'HG_SHARE_BASE_DIR': '/builds/hg-shared',
        'MOZ_OBJDIR': MOZ_OBJDIR,
        # SYMBOL_SERVER_HOST is dictated from build_pool_specifics.py
        'SYMBOL_SERVER_HOST': "%(symbol_server_host)s",
        'SYMBOL_SERVER_USER': 'ffxbld',
        'SYMBOL_SERVER_PATH': '/mnt/netapp/breakpad/symbols_ffx/',
        'SYMBOL_SERVER_SSH_KEY': "/home/mock_mozilla/.ssh/ffxbld_dsa",
        'POST_SYMBOL_UPLOAD_CMD': '/usr/local/bin/post-symbol-upload.py',
        'TINDERBOX_OUTPUT': '1',
        'TOOLTOOL_CACHE': '/builds/tooltool_cache',
        'TOOLTOOL_HOME': '/builds',
        'MOZ_CRASHREPORTER_NO_REPORT': '1',
        'CCACHE_DIR': '/builds/ccache',
        'CCACHE_COMPRESS': '1',
        'CCACHE_UMASK': '002',
        'LC_ALL': 'C',
        'XPCOM_DEBUG_BREAK': 'stack-and-abort',
        # 64 bit specific
        'PATH': '/tools/buildbot/bin:/usr/local/bin:/usr/lib64/ccache:/bin:\
/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/tools/git/bin:/tools/python27/bin:\
/tools/python27-mercurial/bin:/home/cltbld/bin',
    },
    'src_mozconfig': 'browser/config/mozconfigs/linux64/\
debug-static-analysis-clang',
    'base_name': 'Linux x86-64 %(branch)s debug static analysis',
    #######################
}
