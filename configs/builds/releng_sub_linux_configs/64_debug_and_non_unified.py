MOZ_OBJDIR = 'obj-firefox'

config = {
    'default_actions': [
        'clobber',
        'pull',
        'setup-mock',
        'build',
        'generate-build-props',
        # 'generate-build-stats', debug skips this action
        'symbols',
        # 'packages',  non-unified skips this action
        # 'upload',  non-unified skips this action
        # 'sendchanges',  non-unified skips this action
        # 'pretty-names', debug skips this action
        # 'check-l10n', debug skips this action
        'check-test',
        'update',  # decided by query_is_nightly()
        'enable-ccache',
        ],
    'platform': 'linux64-debug-nonunified',
    'mock_files': [
        ('/home/cltbld/.ssh', '/home/mock_mozilla/.ssh'),
        ('/home/cltbld/.hgrc', '/builds/.hgrc'),
        ('/builds/gapi.data', '/builds/gapi.data'),
    ],
    "enable_talos_sendchange": False,  # debug does not fire a talos sendchange
    'enable_signing': False,
    'upload_symbols': False,

    #### 64 bit build specific #####
    'env': {
        'DISPLAY': ':2',
        'HG_SHARE_BASE_DIR': '/builds/hg-shared',
        'MOZ_OBJDIR': MOZ_OBJDIR,
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
        'LD_LIBRARY_PATH': '/tools/gcc-4.3.3/installed/lib64:\
%s/dist/bin' % (MOZ_OBJDIR,),
        },
    'src_mozconfig': 'browser/config/mozconfigs/linux64/debug-nonunified',
    'base_name': 'Linux x86-64 %(branch)s leak test',
    #######################
}
