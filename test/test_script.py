import os
import shutil
import subprocess
import sys
import unittest

try:
    import json
except:
    import simplejson as json

import script

class TestScript(unittest.TestCase):
    def testMkdirRmtree(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        if os.path.exists('test_dir'):
            if os.path.isdir('test_dir'):
                shutil.rmtree('test_dir')
            else:
                os.remove('test_dir')
        self.assertFalse(os.path.exists('test_dir'))
        s.mkdir_p('test_dir/foo/bar/baz')
        self.assertTrue(os.path.isdir('test_dir/foo/bar/baz'))
        s.rmtree('test_dir')
        self.assertFalse(os.path.exists('test_dir'))
        s.rmtree('test_logs')
