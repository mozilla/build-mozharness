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
        if os.path.exists('test_logs'):
            shutil.rmtree('test_logs')
        if os.path.exists('localconfig.json'):
            os.remove('localconfig.json')

    def testHelperFunctions(self):
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
        s.downloadFile("http://www.google.com", file_name="test_dir/google",
                       error_level="ignore")
        self.assertTrue(os.path.exists('test_dir/google'))
        contents1 = s.getOutputFromCommand("cat test_dir/google")
        fh = open("test_dir/google")
        contents2 = fh.read()
        fh.close()
        self.assertEqual(contents1, contents2)
        self.assertEqual(s.runCommand("cat google", cwd="test_dir"), 0)
        s.runCommand("rm test_dir/google")
        self.assertFalse(os.path.exists('test_dir/google'))
        s.rmtree('test_dir')
        self.assertFalse(os.path.exists('test_dir'))
        self.cleanup()

    def testSummary(self):
        self.cleanup()
        s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        info_logsize = os.path.getsize("test_logs/test_info.log")
        self.assertTrue(info_logsize > 0)
        s.addSummary('one')
        info_logsize2 = os.path.getsize("test_logs/test_info.log")
        self.assertTrue(info_logsize < info_logsize2)
        warning_logsize = os.path.getsize("test_logs/test_warning.log")
        s.addSummary('two', level="warning")
        warning_logsize2 = os.path.getsize("test_logs/test_warning.log")
        self.assertTrue(warning_logsize < warning_logsize2)
        info_logsize = os.path.getsize("test_logs/test_info.log")
        warning_logsize = os.path.getsize("test_logs/test_warning.log")
        s.summary()
        info_logsize2 = os.path.getsize("test_logs/test_info.log")
        warning_logsize2 = os.path.getsize("test_logs/test_warning.log")
        self.assertTrue(info_logsize < info_logsize2)
        self.assertTrue(warning_logsize < warning_logsize2)
        self.cleanup()
