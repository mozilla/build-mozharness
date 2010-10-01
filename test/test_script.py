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
        self.assertFalse(os.path.exists('test_dir'),
                         msg="testHelperFunctions() cleanup failed")
        s.mkdir_p('test_dir/foo/bar/baz')
        self.assertTrue(os.path.isdir('test_dir/foo/bar/baz'),
                        msg="mkdir_p error")
        s.mkdir_p('test_dir/foo/bar/baz')
        self.assertTrue(os.path.isdir('test_dir/foo/bar/baz'),
                        msg="mkdir_p error when dir exists")
        s.downloadFile("http://www.google.com", file_name="test_dir/google",
                       error_level="ignore")
        self.assertTrue(os.path.exists('test_dir/google'),
                        msg="error downloading google.com")
        contents1 = s.getOutputFromCommand("cat test_dir/google")
        fh = open("test_dir/google")
        contents2 = fh.read()
        fh.close()
        self.assertEqual(contents1, contents2,
                         msg="getOutputFromCommand('cat file') differs from fh.read")
        self.assertEqual(s.runCommand("cat google", cwd="test_dir"), 0,
                         msg="runCommand('cat file') did not exit 0")
        s.runCommand("rm test_dir/google")
        self.assertFalse(os.path.exists('test_dir/google'),
                         msg="runCommand('rm file') did not remove file")
        s.rmtree('test_dir')
        self.assertFalse(os.path.exists('test_dir'),
                         msg="rmtree unsuccessful")
        s.rmtree('test_dir')
        self.assertFalse(os.path.exists('test_dir'),
                         msg="2nd rmtree unsuccessful")
        self.cleanup()

    def testSummary(self):
        self.cleanup()
        s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        info_logsize = os.path.getsize("test_logs/test_info.log")
        self.assertTrue(info_logsize > 0,
                        msg="initial info logfile missing/size 0")
        s.addSummary('one')
        info_logsize2 = os.path.getsize("test_logs/test_info.log")
        self.assertTrue(info_logsize < info_logsize2,
                        msg="addSummary() not logged")
        warning_logsize = os.path.getsize("test_logs/test_warning.log")
        s.addSummary('two', level="warning")
        warning_logsize2 = os.path.getsize("test_logs/test_warning.log")
        self.assertTrue(warning_logsize < warning_logsize2,
                     msg="addSummary(level='warning') not logged in warning log")
        info_logsize = os.path.getsize("test_logs/test_info.log")
        warning_logsize = os.path.getsize("test_logs/test_warning.log")
        s.summary()
        info_logsize2 = os.path.getsize("test_logs/test_info.log")
        warning_logsize2 = os.path.getsize("test_logs/test_warning.log")
        self.assertTrue(info_logsize < info_logsize2,
                        msg="summary() didn't log to info")
        self.assertTrue(warning_logsize < warning_logsize2,
                        msg="summary() with warning didn't log to warning")
        self.cleanup()

    def testMercurial(self):
        self.cleanup()
        s = script.MercurialScript(initial_config_file='test/test.json')
        s.mkdir_p('test_dir')
        s.runCommand("touch test_dir/tools")
        s.scmCheckout("http://hg.mozilla.org/build/tools",
                      parent_dir="test_dir", clobber=True)
        self.assertTrue(os.path.isdir("test_dir/tools"))
        s.scmCheckout("http://hg.mozilla.org/build/tools",
                      dir_name="test_dir/tools", halt_on_failure=False)
        s.rmtree('test_dir')
        self.cleanup()
