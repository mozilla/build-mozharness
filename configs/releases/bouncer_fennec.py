# lint_ignore=E501
config = {
    "shipped-locales-url": "https://hg.mozilla.org/%(repo)s/raw-file/%(revision)s/mobile/android/locales/all-locales",    
    "products": {
        "installer": {
            "product-name": "Fennec-%(version)s",
            "ssl-only": False,
            "add-locales": True,
            "paths": {
                "android": {
                    "path": "/mobile/releases/%(version)s/android/:lang/fennec-%(version)s.android-arm.apk",
                    "bouncer-platform": "android",
                },
                "android-x86": {
                    "path": "/mobile/releases/%(version)s/android-x86/:lang/fennec-%(version)s.android-x86.apk",
                    "bouncer-platform": "android-x86",
                },
            },
        },
    },   
}