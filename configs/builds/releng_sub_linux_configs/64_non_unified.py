config = {
    'default_actions': [
        'clobber',
        'pull',
        'setup-mock',
        'build',
        'generate-build-props',
        'generate-build-stats',
        'symbols',
        # 'packages',
        # 'upload',
        # 'sendchanges',
        'pretty-names',
        'check-l10n',
        # 'check-test',
        'update',  # decided by query_is_nightly()
        'enable-ccache',
        ],
    'platform': 'linux64-nonunified',

    #### 64 bit build specific #####
    'src_mozconfig': 'browser/config/mozconfigs/linux64/nightly-nonunified',
    #######################
}
