#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla.
#
# The Initial Developer of the Original Code is
# the Mozilla Foundation <http://www.mozilla.org/>.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Aki Sasaki <aki@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""Mozilla-specific signing methods.
"""

import os
import re

from mozharness.base.errors import BaseErrorList
from mozharness.base.log import ERROR, FATAL
from mozharness.base.signing import BaseSigningMixin

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
        try:
            fh = open(snippet_path, 'w')
            fh.write(contents)
            fh.close()
        except:
            self.log("Unable to write complete snippet to %s!" % snippet_path,
                     level=error_level)
            return False
        else:
            return True



# MobileSigningMixin {{{1
class MobileSigningMixin(SigningMixin):
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
