config = {
    'default_actions': [
        'clobber',
        'clone-tools',
        # 'setup-mock', windows do not use mock
        'build',
        'sendchanges',
        'generate-build-stats',
        'update',  # decided by query_is_nightly()
    ],
    'stage_platform': 'win32-nonunified',
    'enable_talos_sendchange': False,
    'enable_unittest_sendchange': False,
    #### 64 bit build specific #####
    'src_mozconfig': 'browser/config/mozconfigs/linux64/win32-nonunified',
    #######################
}
