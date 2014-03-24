MOZ_OBJDIR = 'obj-firefox'

config = {
    'default_actions': [
        'clobber',
        'pull',
        'setup-mock',
        'build',
        'generate-build-props',
        # 'generate-build-stats', asan skips this action
        'symbols',
        'packages',
        'upload',
        'sendchanges',
        # 'pretty-names', asan skips this action
        # 'check-l10n', asan skips this action
        'check-test',
        'update',  # decided by query_is_nightly()
        'enable-ccache',
    ],
    'platform': 'linux64-asan',
    'purge_minsize': 12,
    'mock_files': [
        ('/home/cltbld/.ssh', '/home/mock_mozilla/.ssh'),
        ('/home/cltbld/.hgrc', '/builds/.hgrc'),
        ('/builds/gapi.data', '/builds/gapi.data'),
    ],
    "enable_talos_sendchange": False,  # asan does not fire a talos sendchange
    'enable_signing': False,  # asan has no MOZ_SIGN_CMD
    'tooltool_manifest_src': "browser/config/tooltool-manifests/linux64/\
asan.manifest",
    'upload_symbols': False,
    "platform_supports_snippets": False,
    "platform_supports_partial": False,
    'platform_supports_post_upload_to_latest': False,

    #### 64 bit build specific #####
    'env': {
        'DISPLAY': ':2',
        'HG_SHARE_BASE_DIR': '/builds/hg-shared',
        'MOZ_OBJDIR': 'obj-firefox',
        # SYMBOL_SERVER_HOST is dictated from build_pool_specifics.py
        'SYMBOL_SERVER_HOST': "%(symbol_server_host)s",
        'SYMBOL_SERVER_USER': 'ffxbld',
        'SYMBOL_SERVER_PATH': '/mnt/netapp/breakpad/symbols_ffx/',
        'SYMBOL_SERVER_SSH_KEY': "/home/mock_mozilla/.ssh/ffxbld_dsa",
        'POST_SYMBOL_UPLOAD_CMD': '/usr/local/bin/post-symbol-upload.py',
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
    },
    'src_mozconfig': 'browser/config/mozconfigs/linux64/nightly-asan',
    'base_name': 'Linux x86-64 %(branch)s asan',
    #######################
}
