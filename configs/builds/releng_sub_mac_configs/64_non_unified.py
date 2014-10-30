config = {
    'default_actions': [
        'clobber',
        'clone-tools',
        # 'setup-mock',
        'build',
        'generate-build-stats',
        'update',  # decided by query_is_nightly()
    ],
    'stage_platform': 'macosx64-nonunified',
    'enable_talos_sendchange': False,
    'enable_unittest_sendchange': False,
    'enable_check_test': False,
    #### 64 bit build specific #####
    'src_mozconfig': 'browser/config/mozconfigs/macosx-universal/nightly-nonunified',
    #######################
}
