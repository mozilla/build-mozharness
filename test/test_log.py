import os
import shutil
import subprocess
import sys
import unittest

import log

class TestLog(unittest.TestCase):
    
    def testLogDir(self):
        tmpDir = "test_log_dir"
        if os.path.exists(tmpDir):
            shutil.rmtree(tmpDir)
        self.assertFalse(os.path.exists(tmpDir))
        l = log.SimpleFileLogger(log_dir=tmpDir, log_name='test',
                                 log_to_console=False)
        self.assertTrue(os.path.exists(tmpDir))
        l.info('blah')
        self.assertTrue(os.path.exists(os.path.join(tmpDir, 'test.log')))
        if os.path.exists(tmpDir):
            shutil.rmtree(tmpDir)
        self.assertFalse(os.path.exists(tmpDir))
