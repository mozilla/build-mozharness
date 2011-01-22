import os
import shutil
import subprocess
import unittest

import mozharness.base.log as log

tmp_dir = "test_log_dir"
log_name = "test"

class TestLog(unittest.TestCase):
    def clean_log_dir(self):
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        self.assertFalse(os.path.exists(tmp_dir))

    def get_log_file_path(self, level=None):
        if level:
            return os.path.join(tmp_dir, "%s_%s.log" % (log_name, level))
        return os.path.join(tmp_dir, "%s.log" % log_name)

    def test_log_dir(self):
        self.clean_log_dir()
        fh = open(tmp_dir, 'w')
        fh.write("foo")
        fh.close()
        l = log.SimpleFileLogger(log_dir=tmp_dir, log_name=log_name,
                                 log_to_console=False)
        self.assertTrue(os.path.exists(tmp_dir))
        l.info('blah')
        self.assertTrue(os.path.exists(self.get_log_file_path()))
        del(l)
        self.clean_log_dir()

    def test_multi_log(self):
        self.clean_log_dir()
        level_dict = {'debug':    [],
                      'ignore':   [],
                      'info':     ['info'],
                      'warning':  ['info', 'warning'],
                      'error':    ['info', 'warning', 'error'],
                      'critical': ['info', 'warning', 'error', 'critical'],
                      'fatal':    ['info', 'warning', 'error', 'critical']}
        filesize_dict = {}
        for log_level in level_dict.keys():
            l = log.MultiFileLogger(log_dir=tmp_dir, log_name=log_name,
                                    log_to_console=False)
            if log_level != "fatal":
                l.log('testing', level=log_level)
            else:
                try:
                    l.fatal('testing')
                except:
                    pass
                else:
                    self.assertEqual(0, 1, msg="fatal() doesn't exit")
            del(l)
            for level in level_dict[log_level]:
                log_path = self.get_log_file_path(level=level)
                self.assertTrue(os.path.exists(log_path))
                filesize = os.path.getsize(log_path)
                self.assertTrue(filesize > filesize_dict.get(log_path, 0))
                filesize_dict[log_path] = filesize
        self.clean_log_dir()

    def test_console_log(self):
        self.clean_log_dir()
        l = log.SimpleFileLogger(log_dir=tmp_dir, log_name=log_name,
                                 log_to_console=True)
        l.warning("This test warning should go to the console.")
        del(l)
        self.clean_log_dir()
