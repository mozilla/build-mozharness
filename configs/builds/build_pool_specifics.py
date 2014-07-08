# this is a dict of pool specific keys/values. As this fills up and more
# fx build factories are ported, we might deal with this differently

config = {
    "staging": {
        'aus2_host': 'dev-stage01.srv.releng.scl3.mozilla.com',
        'balrog_api_root': 'https://aus4-admin-dev.allizom.org',
        'balrog_username': 'stage-ffxbld',
        # if not clobberer_url, only clobber 'abs_work_dir'
        # if true: possibly clobber, clobberer, and purge_builds
        # see PurgeMixin for clobber() conditions
        'clobberer_url': 'http://clobberer-stage.pvt.build.mozilla.org/index.php',
        # staging we should use MozillaTest
        # but in production we let the self.branch decide via
        # self._query_graph_server_branch_name()
        "graph_server_branch_name": "MozillaTest",
        "hgtool_base_bundle_urls": [
            'http://dev-stage01.build.mozilla.org/pub/mozilla'
            '.org/firefox/bundles',
        ],
        'stage_server': 'dev-stage01.srv.releng.scl3.mozilla.com',
        'symbol_server_host': "dev-stage01.srv.releng.scl3.mozilla.com",
        "sendchange_masters": ["dev-master1.srv.releng.scl3.mozilla.com:9038"],
        'graph_server': 'graphs.allizom.org',
    },
    "production": {
        'aus2_host': 'aus3-staging.mozilla.org',
        'balrog_api_root': 'https://aus4-admin.mozilla.org',
        'balrog_username': 'ffxbld',
        # if not clobberer_url, only clobber 'abs_work_dir'
        # if true: possibly clobber, clobberer, and purge_builds
        # see PurgeMixin for clobber() conditions
        'clobberer_url': 'http://clobberer.pvt.build.mozilla.org/index.php',
        'graph_server': 'graphs.mozilla.org',
        "hgtool_base_bundle_urls": [
            'https://ftp-ssl.mozilla.org/pub/mozilla.org/firefox/bundles'
        ],
        "sendchange_masters": ["buildbot-master81.build.mozilla.org:9301"],
        'stage_server': 'stage.mozilla.org',
        'symbol_server_host': "symbolpush.mozilla.org",
    },
}
