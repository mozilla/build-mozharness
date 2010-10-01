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
    def cleanup(self):
        if os.path.exists('test_logs')
            shutil.rmtree('test_logs')
        if os.path.exists('localconfig.json')
            os.remove('localconfig.json')

    def testMkdirRmtree(self):
        self.cleanup()
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
        self.cleanup()

    def testSummary(self):
        self.cleanup()
        s = script.BaseScript(initial_config_file='test/test.json')
        s.addSummary('one')
        s.addSummary('two')
        s.addSummary('three')
        s.summary()
        # TODO add actual test
        self.cleanup()
