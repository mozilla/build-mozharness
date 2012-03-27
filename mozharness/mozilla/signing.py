#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Mozilla-specific signing methods.
"""

import os
import re

from mozharness.base.errors import BaseErrorList
from mozharness.base.log import ERROR, FATAL
from mozharness.base.signing import AndroidSigningMixin, BaseSigningMixin

AndroidSignatureVerificationErrorList = BaseErrorList + [{
    "regex": re.compile(r'''^Invalid$'''),
    "level": FATAL,
    "explanation": "Signature is invalid!"
},{
    "substr": "filename not matched",
    "level": ERROR,
},{
    "substr": "ERROR: Could not unzip",
    "level": ERROR,
},{
    "regex": re.compile(r'''Are you sure this is a (nightly|release) package'''),
    "level": FATAL,
    "explanation": "Not signed!"
}]

# TODO I'm not sure how many templates we will need.
# This will be sufficient for the moment.
SNIPPET_TEMPLATE = """version=1
type=complete
url=%(url)s
hashFunction=sha512
hashValue=%(sha512_hash)s
size=%(size)d
build=%(buildid)s
appv=%(version)s
extv=%(version)s
"""


# SigningMixin {{{1

class SigningMixin(BaseSigningMixin):
    """Generic signing helper methods.
    """
    # Should this write to file too?
    def create_complete_snippet(self, binary_path, version, buildid,
                                url, snippet_dir, snippet_file="complete.txt",
                                size=None, sha512_hash=None,
                                error_level=ERROR):
        """Create a complete snippet, and writes to file.
        Returns True for success, False for failure.
        """
        self.info("Creating complete snippet for %s." % binary_path)
        if not os.path.exists(binary_path):
            self.error("Can't create complete snippet: %s doesn't exist!" % binary_path)
            return False
        replace_dict = {
            'version': version,
            'buildid': buildid,
            'url': url,
        }
        # Allow these to be generated beforehand since we may be generating
        # many snippets for the same binary_path, and calculating them
        # multiple times isn't efficient.
        if size:
            replace_dict['size'] = size
        else:
            replace_dict['size'] = self.query_filesize(binary_path)
        if sha512_hash:
            replace_dict['sha512_hash'] = sha512_hash
        else:
            replace_dict['sha512_hash'] = self.query_sha512sum(binary_path)
        contents = SNIPPET_TEMPLATE % replace_dict
        self.mkdir_p(snippet_dir)
        snippet_path = os.path.join(snippet_dir, snippet_file)
        if self.write_to_file(snippet_path, contents, verbose=False) is None:
            self.log("Unable to write complete snippet to %s!" % snippet_path,
                     level=error_level)
            return False
        else:
            return True



# MobileSigningMixin {{{1
class MobileSigningMixin(AndroidSigningMixin, SigningMixin):
    def verify_android_signature(self, apk, script=None, key_alias="nightly",
                                 tools_dir="tools/", env=None):
        """Runs mjessome's android signature verification script.
        This currently doesn't check to see if the apk exists; you may want
        to do that before calling the method.
        """
        c = self.config
        dirs = self.query_abs_dirs()
        if script is None:
            script = c.get('signature_verification_script')
        if env is None:
            env = self.query_env()
        return self.run_command(
            [script, "--tools-dir=%s" % tools_dir, "--%s" % key_alias,
             "--apk=%s" % apk],
            cwd=dirs['abs_work_dir'],
            env=env,
            error_list=AndroidSignatureVerificationErrorList
        )
