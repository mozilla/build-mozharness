config = {
    "upload_env": {
        "UPLOAD_USER": "ffxbld",
        "UPLOAD_SSH_KEY": "~/.ssh/ffxbld_dsa",
        "UPLOAD_HOST": "dev-stage01.srv.releng.scl3.mozilla.com",
        "POST_UPLOAD_CMD": "post_upload.py -b %(branch)s-l10n -p firefox -i %(buildid)s --release-to-latest --release-to-dated",
        "UPLOAD_TO_TEMP": "1"
    },
}
