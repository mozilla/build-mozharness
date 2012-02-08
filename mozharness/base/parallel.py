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
"""Generic ways to parallelize jobs.
"""

# ChunkingMixin {{{1

class ChunkingMixin(object):
    """Generic signing helper methods.
    """
    def query_chunked_list(self, possible_list, this_chunk, total_chunks,
                           sort=False):
        """Split a list of items into a certain number of chunks and
        return the subset of that will occur in this chunk.

        Ported from build.l10n.getLocalesForChunk in build/tools.
        """
        if sort:
            possible_list = sorted(possible_list)
        else:
            # Copy to prevent altering
            possible_list = possible_list[:]
        length = len(possible_list)
        for c in range(1, total_chunks + 1):
            n = length / total_chunks
            # If the total number of items isn't evenly divisible by the
            # number of chunks, we need to append one more onto some chunks
            if c <= (length % total_chunks):
                n += 1
            if c == this_chunk:
                return possible_list[0:n]
            del possible_list[0:n]
