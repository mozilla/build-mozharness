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

    def getLogFilePath(self, level=None):
        if level:
            return os.path.join(tmp_dir, "%s_%s.log" % (log_name, level))
        return os.path.join(tmp_dir, "%s.log" % log_name)

    def testLogDir(self):
        self.cleanLogDir()
        l = log.SimpleFileLogger(log_dir=tmp_dir, log_name=log_name,
                                 log_to_console=False)
        self.assertTrue(os.path.exists(tmp_dir))
        l.info('blah')
        self.assertTrue(os.path.exists(self.getLogFilePath()))
        self.cleanLogDir()

    def testMultiLog(self):
        self.cleanLogDir()
        l = log.MultiFileLogger(log_dir=tmp_dir, log_name=log_name,
                                log_to_console=False)
        level_dict = {'info':     ['info'],
                      'warning':  ['info', 'warning'],
                      'error':    ['info', 'warning', 'error'],
                      'critical': ['info', 'warning', 'error', 'critical'],
                      'fatal':    ['info', 'warning', 'error', 'critical']}
        filesize_dict = {}
        for log_level in level_dict.keys():
            if log_level != "fatal":
                l.log('testing', level=log_level)
            else:
                try:
                    l.fatal('testing')
                except:
                    pass
                else:
                    self.assertIsNotNone(None, msg="fatal() doesn't exit")
            for level in level_dict[log_level]:
                log_path = self.getLogFilePath(level=level)
                self.assertTrue(os.path.exists(log_path))
                filesize = os.path.getsize(log_path)
                self.assertTrue(filesize > filesize_dict.get(log_path, 0))
                filesize_dict[log_path] = filesize
        self.cleanLogDir()

    def testMultiLogDebug(self):
        self.cleanLogDir()
        l = log.MultiFileLogger(log_dir=tmp_dir, log_name=log_name,
                                log_to_console=False)
        l.debug('debug message')
        self.assertFalse(os.path.exists(self.getLogFilePath(level='debug')))
        self.cleanLogDir()
