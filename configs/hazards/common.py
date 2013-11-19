HG_SHARE_BASE_DIR = "/builds/hg-shared"

PYTHON_DIR = "/tools/python27"
#GCC_DIR = "/tools/gcc-4.7.3-0moz1"
GCC_DIR = "/tools/gcc-4.7.2-0moz1"
#GCC_RPM = "gcc473_0moz1"
GCC_RPM = "gcc472_0moz1"

config = {
    "log_name": "spidermonkey",
    "shell-objdir": "obj-opt-js",
    "analysis-dir": "analysis",
    "source-objdir": "obj-analyzed",

    "sixgill": "/usr/libexec/sixgill",
    "sixgill_bin": "/usr/bin",
    "python": PYTHON_DIR + "/bin/python2.7",

    "exes": { 'hgtool.py': 'tools/buildfarm/utils/hgtool.py' },

    "purge_minsize": 15,
    "force_clobber": True,
    'vcs_share_base': HG_SHARE_BASE_DIR,

    "repos": [{
        "repo": "http://hg.mozilla.org/build/tools",
        "revision": "default",
        "dest": "tools"
    }],

    "upload_remote_baseuri": 'http://ftp.mozilla.org/',

    # Mock.
    "mock_packages": [
        "autoconf213", "mozilla-python27-mercurial", "ccache",
        "zip", "zlib-devel", "glibc-static",
        "openssh-clients", "mpfr", "wget", "rsync",

        # For the analysis
        GCC_RPM,

        # For building the JS shell
        "gmp-devel", "nspr", "nspr-devel", "sixgill",

        # For building the browser
        "dbus-devel", "dbus-glib-devel", "hal-devel",
        "libICE-devel", "libIDL-devel",

        # For mach resource-usage
        "python-psutil",

        'zip', 'git',
        'libstdc++-static', 'perl-Test-Simple', 'perl-Config-General',
        'gtk2-devel', 'libnotify-devel', 'yasm',
        'alsa-lib-devel', 'libcurl-devel',
        'wireless-tools-devel', 'libX11-devel',
        'libXt-devel', 'mesa-libGL-devel',
        'gnome-vfs2-devel', 'GConf2-devel', 'wget',
        'mpfr', # required for system compiler
        'xorg-x11-font*', # fonts required for PGO
        'imake', # required for makedepend!?!
        'pulseaudio-libs-devel',
        'freetype-2.3.11-6.el6_1.8.x86_64',
        'freetype-devel-2.3.11-6.el6_1.8.x86_64',
        'gstreamer-devel', 'gstreamer-plugins-base-devel',
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
