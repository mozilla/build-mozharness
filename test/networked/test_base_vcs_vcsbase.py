import os
import shutil
import subprocess
import sys
import unittest

try:
    import simplejson as json
except ImportError:
    import json

import mozharness.base.errors as errors
import mozharness.base.vcs.vcsbase as vcsbase

test_string = '''foo
bar
baz'''

def cleanup():
    if os.path.exists('test_logs'):
        shutil.rmtree('test_logs')
    if os.path.exists('test_dir'):
        if os.path.isdir('test_dir'):
            shutil.rmtree('test_dir')
        else:
            os.remove('test_dir')
    for filename in ('localconfig.json', 'localconfig.json.bak'):
        if os.path.exists(filename):
            os.remove(filename)

class TestMercurialScript(unittest.TestCase):
    def setUp(self):
        cleanup()

    def tearDown(self):
        cleanup()

    def test_mercurial_script(self):
        s = vcsbase.MercurialScript(initial_config_file='test/test.json')
        s.vcs_checkout(repo="http://hg.mozilla.org/build/tools",
                       dest="test_dir/tools")
        self.assertTrue(os.path.isdir("test_dir/tools"))
