# this is a dict of branch specific keys/values. As this fills up and more
# fx build factories are ported, we might deal with this differently

# we should be able to port this in-tree and have the respective repos and
# revisions handle what goes on in here. Tracking: bug 978510

config = {
    "mozilla-central": {
        # nightly stuff
        "update_channel": "nightly",
        "create_snippets": True,
        "create_partial": True,

        "graph_server_branch_name": "Firefox",
        # 'mozilla-central' is the default
        "repo_path": 'mozilla-central',
        'use_branch_in_symbols_extra_buildid': False,
    },
    "cypress": {
        # buildbot doesn't do nightlies for this branch

        # for branches that are pretty similar to m-c and only require a
        # slight change like 'repo_path', we may not need an item for each
        "repo_path": 'projects/cypress',
    }
}
