import os

config = {
    'default_actions': [
        'clobber',
        'clone-tools',
        'setup-mock',
        'build',
        # 'generate-build-stats',
        'update',  # decided by query_is_nightly()
    ],
    'stage_platform': 'linux64-mulet',
    'stage_product': 'b2g',
    'tooltool_manifest_src': "b2g/dev/config/tooltool-manifests/linux64/releng.manifest",
    'platform_supports_post_upload_to_latest': False,
    'enable_signing': False,
    'enable_talos_sendchange': False,
    'enable_count_ctors': False,
    'enable_check_test': False,
    #### 64 bit build specific #####
    'env': {
        'MOZBUILD_STATE_PATH': os.path.join(os.getcwd(), '.mozbuild'),
        'MOZ_AUTOMATION': '1',
        'DISPLAY': ':2',
        'HG_SHARE_BASE_DIR': '/builds/hg-shared',
        'MOZ_OBJDIR': 'obj-firefox',
        'TINDERBOX_OUTPUT': '1',
        'TOOLTOOL_CACHE': '/builds/tooltool_cache',
        'TOOLTOOL_HOME': '/builds',
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
    'src_mozconfig': 'b2g/dev/config/mozconfigs/linux64/mulet',
    #######################
}