import os
from mozharness.base.python import VirtualenvMixin
from mozharness.base.script import PostScriptRun

blobupload_config_options = [
    [["--blob-upload-branch"],
    {"dest": "blob_upload_branch",
     "help": "Branch for blob server's metadata",
    }],
    [["--blob-upload-server"],
    {"dest": "blob_upload_servers",
     "action": "extend",
     "help": "Blob servers's location",
    }]
    ]


class BlobUploadMixin(VirtualenvMixin):
    """Provides mechanism to automatically upload files written in
    MOZ_UPLOAD_DIR to the blobber upload server at the end of the
    running script.

    This is dependent on ScriptMixin.
    The testing script inheriting this class is to specify as cmdline
    options the <blob-upload-branch> and <blob-upload-server>

    """
    #TODO: documentation about the Blobber Server on wiki
    def __init__(self, *args, **kwargs):
        requirements = [
            'blobuploader==0.9',
        ]
        super(BlobUploadMixin, self).__init__(*args, **kwargs)
        for req in requirements:
            self.register_virtualenv_module(req, method='pip')

    def upload_blobber_files(self):
        self.debug("Check branch and server cmdline options.")
        if self.config.get('blob_upload_branch') and \
            (self.config.get('blob_upload_servers') or
             self.config.get('default_blob_upload_servers')):

            self.info("Blob upload gear active.")
            upload = [self.query_python_path("blobberc.py")]

            dirs = self.query_abs_dirs()
            self.debug("Get the directory from which to upload the files.")
            if dirs.get('abs_blob_upload_dir'):
                blob_dir = dirs['abs_blob_upload_dir']
            else:
                self.warning("Couldn't find the blob upload folder's path!")
                return

            if not os.path.isdir(blob_dir):
                self.warning("Blob upload directory does not exist!")
                return

            if not os.listdir(blob_dir):
                self.info("There are no files to upload in the directory. "
                          "Skipping the blob upload mechanism ...")
                return

            self.info("Preparing to upload files from %s." % blob_dir)
            blob_branch = self.config.get('blob_upload_branch')
            blob_servers_list = self.config.get('blob_upload_servers',
                               self.config.get('default_blob_upload_servers'))

            servers = []
            for server in blob_servers_list:
                servers.extend(['-u', server])
            branch = ['-b', blob_branch]
            dir_to_upload = ['-d', blob_dir]
            self.info("Files from %s are to be uploaded with <%s> branch at "
                      "the following location(s): %s" % (blob_dir, blob_branch,
                      ", ".join(["%s" % s for s in blob_servers_list])))

            # call blob client to upload files to server
            self.run_command(upload + servers + branch + dir_to_upload)
        else:
            self.warning("Blob upload gear skipped. Missing cmdline options.")

    @PostScriptRun
    def _upload_blobber_files(self):
        self.upload_blobber_files()
