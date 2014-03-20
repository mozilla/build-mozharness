# lint_ignore=E501
config = {
    "shipped-locales-url": "https://hg.mozilla.org/%(repo)s/raw-file/%(revision)s/mail/locales/shipped-locales",
    "product-name": "Thunderbird-%(version)s",
    "ssl-only-product-name": "Thunderbird-%(version)s-SSL",
    "complete-updates-product-name": "Thunderbird-%(version)s-Complete",
    "partial-updates-product-name": "Thunderbird-%(version)s-Partial-%(prev_version)s",
    "add-ssl-only-product": True,
    "platform-config": {
        "linux": {
            "installer": "/thunderbird/releases/%(version)s/linux-i686/:lang/thunderbird-%(version)s.tar.bz2",
            "complete-mar": "/thunderbird/releases/%(version)s/update/linux-i686/:lang/thunderbird-%(version)s.complete.mar",
            "partial-mar": "/thunderbird/releases/%(version)s/update/linux-i686/:lang/thunderbird-%(prev_version)s-%(version)s.partial.mar",
            "bouncer-platform": "linux",
        },
        "linux64": {
            "installer": "/thunderbird/releases/%(version)s/linux-x86_64/:lang/thunderbird-%(version)s.tar.bz2",
            "complete-mar": "/thunderbird/releases/%(version)s/update/linux-x86_64/:lang/thunderbird-%(version)s.complete.mar",
            "partial-mar": "/thunderbird/releases/%(version)s/update/linux-x86_64/:lang/thunderbird-%(prev_version)s-%(version)s.partial.mar",
            "bouncer-platform": "linux64",
        },
        "macosx64": {
            "installer": "/thunderbird/releases/%(version)s/mac/:lang/Thunderbird%%20%(version)s.dmg",
            "complete-mar": "/thunderbird/releases/%(version)s/update/mac/:lang/thunderbird-%(version)s.complete.mar",
            "partial-mar": "/thunderbird/releases/%(version)s/update/mac/:lang/thunderbird-%(prev_version)s-%(version)s.partial.mar",
            "bouncer-platform": "osx",
        },
        "win32": {
            "installer": "/thunderbird/releases/%(version)s/win32/:lang/Thunderbird%%20Setup%%20%(version)s.exe",
            "complete-mar": "/thunderbird/releases/%(version)s/update/win32/:lang/thunderbird-%(version)s.complete.mar",
            "partial-mar": "/thunderbird/releases/%(version)s/update/win32/:lang/thunderbird-%(prev_version)s-%(version)s.partial.mar",
            "bouncer-platform": "win",
        },
        "opensolaris-i386": {
            "installer": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(version)s.en-US.opensolaris-i386.tar.bz2",
            "complete-mar": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(version)s.en-US.opensolaris-i386.complete.mar",
            "partial-mar": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(prev_version)s-%(version)s.en-US.opensolaris-i386.partial.mar",
            "bouncer-platform": "opensolaris-i386",
        },
        "opensolaris-sparc": {
            "installer": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(version)s.en-US.opensolaris-sparc.tar.bz2",
            "complete-mar": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(version)s.en-US.opensolaris-sparc.complete.mar",
            "partial-mar": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(prev_version)s-%(version)s.en-US.opensolaris-sparc.partial.mar",
            "bouncer-platform": "opensolaris-sparc",
        },
        "solaris-i386": {
            "installer": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(version)s.en-US.solaris-i386.tar.bz2",
            "complete-mar": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(version)s.en-US.solaris-i386.complete.mar",
            "partial-mar": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(prev_version)s-%(version)s.en-US.solaris-i386.partial.mar",
            "bouncer-platform": "solaris-i386",
        },
        "solaris-sparc": {
            "installer": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(version)s.en-US.solaris-sparc.tar.bz2",
            "complete-mar": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(version)s.en-US.solaris-sparc.complete.mar",
            "partial-mar": "/thunderbird/releases/%(version)s/contrib/solaris_tarball/thunderbird-%(prev_version)s-%(version)s.en-US.solaris-sparc.partial.mar",
            "bouncer-platform": "solaris-sparc",
        },
    },
}
