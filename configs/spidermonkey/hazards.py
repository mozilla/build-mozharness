HG_SHARE_BASE_DIR = "/builds/hg-shared"

PYTHON_DIR = "/tools/python27"
GCC_DIR = "/tools/gcc-4.7.3-0moz1"
GCC_RPM = "gcc473_0moz1"

config = {
    "log_name": "spidermonkey",
    "shell-objdir": "obj-opt-js",
    "analysis-dir": "analysis",
    "source-objdir": "obj-analyzed",

    "sixgill": "/usr/libexec/sixgill",
    "sixgill_bin": "/usr/bin",
    "python": PYTHON_DIR + "/bin/python2.7",

    "exes": { 'hgtool.py': 'tools/buildfarm/utils/hgtool.py' },

    "purge_minsize": 10,
    "force_clobber": True,
    'vcs_share_base': HG_SHARE_BASE_DIR,

    "repos": [{
        "repo": "http://hg.mozilla.org/build/tools",
        "revision": "default",
        "dest": "tools"
    }],

    # Mock.
    "mock_packages": [
        "autoconf213", "mozilla-python27-mercurial", "ccache",
        "zip", "zlib-devel", "glibc-static",
        "openssh-clients", "mpfr", "wget", "rsync",
        GCC_RPM,
        "gmp-devel", "nspr", "nspr-devel", "sixgill"
    ],
    "mock_files": [
        ("/home/cltbld/.ssh", "/home/mock_mozilla/.ssh"),
    ],
    "mock_env_replacements": {
        "pythondir": PYTHON_DIR,
        "gccdir": GCC_DIR,
    },
    "mock_env": {
        "PATH": "%(pythondir)s/bin:%(gccdir)s/bin:%(PATH)s",
    },
}
