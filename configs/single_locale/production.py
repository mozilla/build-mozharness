config = {
    "upload_env": {
        "UPLOAD_USER": "ffxbld",
        "UPLOAD_SSH_KEY": "~/.ssh/ffxbld_rsa",
        "UPLOAD_HOST": "stage.mozilla.org",
        "POST_UPLOAD_CMD": "post_upload.py -b %(branch)s-l10n -p firefox -i %(buildid)s --release-to-latest --release-to-dated",
        "UPLOAD_TO_TEMP": "1"
    },
}
