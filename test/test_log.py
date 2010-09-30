import os
import shutil
import subprocess
import unittest

import log

tmp_dir = "test_log_dir"
log_name = "test"

class TestLog(unittest.TestCase):
    def cleanLogDir(self):
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        self.assertFalse(os.path.exists(tmp_dir))

    def testLogDir(self):
        self.cleanLogDir()
        l = log.SimpleFileLogger(log_dir=tmp_dir, log_name=log_name,
                                 log_to_console=False)
        self.assertTrue(os.path.exists(tmp_dir))
        l.info('blah')
        self.assertTrue(os.path.exists(os.path.join(tmp_dir, '%s.log' % log_name)))
        self.cleanLogDir()

    def testMultiLog(self):
        self.cleanLogDir()
        l = log.MultiFileLogger(log_dir=tmp_dir, log_name=log_name,
                                log_to_console=False)
        l.critical('critical message')
        for level in log.BaseLogger.LEVELS:
            if level not in ('debug', 'fatal'):
                log_file = os.path.join(tmp_dir, "%s_%s.log" % (log_name, level))
                self.assertTrue(os.path.exists(log_file))
                self.assertTrue(os.path.getsize(log_file) > 0)
        self.cleanLogDir()
