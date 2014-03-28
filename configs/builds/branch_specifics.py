# this is a dict of branch specific keys/values. As this fills up and more
# fx build factories are ported, we might deal with this differently

# we should be able to port this in-tree and have the respective repos and
# revisions handle what goes on in here. Tracking: bug 978510

# example config and explanation of how it works:
# config = {
#     # if a branch matches a key below, override items in self.config with
#     # items in the key's value.
#     # this override can be done for every platform or at a platform level
#     '<branch-name>': {
#         # global config items (applies to all platforms and build types)
#         'repo_path': "projects/<branch-name>",
#         'graph_server_branch_name': "Firefox",
#
#         # platform config items (applies to specific platforms)
#         'platform_overrides': {
#             # if a platform matches a key below, override items in
#             # self.config with items in the key's value
#             'linux64-debug': {
#                 'upload_symbols': False,
#             },
#             'win64': {
#                 'enable_checktests': False,
#             },
#         }
#     },
# }

config = {
    ### release branches
    "mozilla-central": {
        "update_channel": "nightly",
        "graph_server_branch_name": "Firefox",
        "repo_path": 'mozilla-central',
        'use_branch_in_symbols_extra_buildid': False,
    },
    'mozilla-release': {
        'repo_path': 'releases/mozilla-release',
        # TODO I think we can remove update_channel since we don't run
        # nightlies for mozilla-release
        'update_channel': 'release',
        'branch_uses_per_checkin_strategy': True,
    },
    'mozilla-beta': {
        'repo_path': 'releases/mozilla-beta',
        # TODO I think we can remove update_channel since we don't run
        # nightlies for mozilla-beta
        'update_channel': 'beta',
        'branch_uses_per_checkin_strategy': True,
    },
    'mozilla-aurora': {
        'repo_path': 'releases/mozilla-aurora',
        'update_channel': 'aurora',
        'branch_uses_per_checkin_strategy': True,
    },
    'mozilla-esr24': {
        'repo_path': 'releases/mozilla-esr24',
        'update_channel': 'nightly-esr24',
        'branch_uses_per_checkin_strategy': True,
    },
    'mozilla-b2g26_v1_2': {
        'repo_path': 'releases/mozilla-b2g26_v1_2',
    },
    'mozilla-b2g28_v1_3': {
        'repo_path': 'releases/mozilla-b2g28_v1_3',
        'update_channel': 'nightly-b2g28',
        # in automation we will run this branch with nightly but we do not
        # create snippets or partials
        "create_snippets": False,
        "create_partial": False
    },
    'mozilla-b2g28_v1_3t': {
        'repo_path': 'releases/mozilla-b2g28_v1_3t',
    },
    'mozilla-b2g18': {
        'repo_path': 'releases/mozilla-aurora',
        'platform_overrides': {
            # removes pulseaudio and gstreamer packages
            'linux64': {
                'mock_packages': [
                    'autoconf213', 'python', 'zip', 'mozilla-python27-mercurial',
                    'git', 'ccache', 'perl-Test-Simple', 'perl-Config-General',
                    'yasm', 'wget',
                    'mpfr',  # required for system compiler
                    'xorg-x11-font*',  # fonts required for PGO
                    'imake',  # required for makedepend!?!
                    ### <-- from releng repo
                    'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
                    'yasm', 'ccache',
                    ###
                    'valgrind', 'dbus-x11',
                    ######## 64 bit specific ###########
                    'glibc-static', 'libstdc++-static',
                    'gtk2-devel', 'libnotify-devel',
                    'alsa-lib-devel', 'libcurl-devel', 'wireless-tools-devel',
                    'libX11-devel', 'libXt-devel', 'mesa-libGL-devel', 'gnome-vfs2-devel',
                    'GConf2-devel',
                    ### from releng repo
                    'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
                    'yasm', 'ccache',
                    ###
                    'freetype-2.3.11-6.el6_1.8.x86_64',
                    'freetype-devel-2.3.11-6.el6_1.8.x86_64'
                ]
            },
            # removes pulseaudio and gstreamer packages
            'linux64-debug': {
                'mock_packages': [
                    'autoconf213', 'python', 'zip', 'mozilla-python27-mercurial',
                    'git', 'ccache', 'perl-Test-Simple', 'perl-Config-General',
                    'yasm', 'wget',
                    'mpfr',  # required for system compiler
                    'xorg-x11-font*',  # fonts required for PGO
                    'imake',  # required for makedepend!?!
                    ### <-- from releng repo
                    'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
                    'yasm', 'ccache',
                    ###
                    'valgrind', 'dbus-x11',
                    ######## 64 bit specific ###########
                    'glibc-static', 'libstdc++-static',
                    'gtk2-devel', 'libnotify-devel',
                    'alsa-lib-devel', 'libcurl-devel', 'wireless-tools-devel',
                    'libX11-devel', 'libXt-devel', 'mesa-libGL-devel', 'gnome-vfs2-devel',
                    'GConf2-devel',
                    ### from releng repo
                    'gcc45_0moz3', 'gcc454_0moz1', 'gcc472_0moz1', 'gcc473_0moz1',
                    'yasm', 'ccache',
                    ###
                    'freetype-2.3.11-6.el6_1.8.x86_64',
                    'freetype-devel-2.3.11-6.el6_1.8.x86_64'
                ]
            },
        },
    },
    'mozilla-b2g18_v1_1_0_hd': {
        'repo_path': 'releases/mozilla-b2g18',
    },

    ### project branches
    'b2g-inbound': {
        'repo_path': 'integration/b2g-inbound',
        'platform_overrides': {
            'win32': {
                'enable_checktests': False,
            },
            'win32-debug': {
                'enable_checktests': False,
            },
            'macosx64': {
                'enable_checktests': False,
            },
            'macosx64-debug': {
                'enable_checktests': False,
            },
        },
    },
    'date': {
        'platform_overrides': {
            # Bug 950206 - Enable 32-bit Windows builds on Date, test those
            # builds on tst-w64-ec2-XXXX
            'win32': {
                'unittest_platform': 'win64',
            },
        },
    },
    'fx-team': {
        'repo_path': 'integration/fx-team',
    },
    'mozilla-inbound': {
        'repo_path': 'integration/mozilla-inbound',
    },
    'services-central': {
        'repo_path': 'services/services-central',
    },
    'ux': {
        "graph_server_branch_name": "UX",
    },

    ### other branches that do not require anything special:
    # 'alder': {},
    # 'ash': {},
    # 'birch': {},
    # 'build-system': {}
    # 'cedar': {},
    # "cypress": {},
    # 'elm': {},
    # 'fig': {},
    # 'graphics': {}
    # 'gum': {},
    # 'holly': {},
    # 'ionmonkey': {},
    # 'jamun': {},
    # 'larch': {},
    # 'maple': {},
    # 'oak': {},
    #'pine': {}
}
