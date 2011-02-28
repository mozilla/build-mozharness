import os
import shutil
import subprocess
import unittest

import mozharness.base.log as log

tmp_dir = "test_log_dir"
log_name = "test"

def clean_log_dir():
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

def get_log_file_path(level=None):
    if level:
        return os.path.join(tmp_dir, "%s_%s.log" % (log_name, level))
    return os.path.join(tmp_dir, "%s.log" % log_name)

class TestLog(unittest.TestCase):
    def setUp(self):
        clean_log_dir()

    def tearDown(self):
        clean_log_dir()

    def test_log_dir(self):
        fh = open(tmp_dir, 'w')
        fh.write("foo")
        fh.close()
        l = log.SimpleFileLogger(log_dir=tmp_dir, log_name=log_name,
                                 log_to_console=False)
        self.assertTrue(os.path.exists(tmp_dir))
        l.info('blah')
        self.assertTrue(os.path.exists(get_log_file_path()))
        del(l)

    def test_console_log(self):
        l = log.SimpleFileLogger(log_dir=tmp_dir, log_name=log_name,
                                 log_to_console=True)
        l.warning("This test warning should go to the console.")
        del(l)

    def test_fatal(self):
        l = log.SimpleFileLogger(log_dir=tmp_dir, log_name=log_name,
                                 log_to_console=True)
        try:
            l.fatal('testing')
        except SystemExit:
            pass
        else:
            self.assertEqual(0, 1, msg="fatal() doesn't SystemExit!")

class TestMultiLog(unittest.TestCase):
    def setUp(self):
        clean_log_dir()

    def tearDown(self):
        clean_log_dir()

    def _test_log_level(self, log_level, log_level_file_list):
        l = log.MultiFileLogger(log_dir=tmp_dir, log_name=log_name,
                                log_to_console=False)
        if log_level != "fatal":
            l.log('testing', level=log_level)
        else:
            try:
                l.fatal('testing')
            except SystemExit:
                pass
        del(l)
        msg = ""
        for level in log_level_file_list:
            log_path = get_log_file_path(level=level)
            if not os.path.exists(log_path):
                msg += "%s doesn't exist!\n" % log_path
            else:
                filesize = os.path.getsize(log_path)
                if not filesize > 0:
                    msg += "%s is size 0!\n" % log_path
        self.assertEqual(msg, "", msg=msg)

    def test_debug(self):
        self._test_log_level('debug', [])

    def test_ignore(self):
        self._test_log_level('ignore', [])

    def test_info(self):
        self._test_log_level('info', ['info'])

    def test_warning(self):
        self._test_log_level('warning', ['info', 'warning'])

    def test_error(self):
        self._test_log_level('error', ['info', 'warning', 'error'])

    def test_critical(self):
        self._test_log_level('critical', ['info', 'warning', 'error',
                                          'critical'])

    def test_fatal(self):
        self._test_log_level('fatal', ['info', 'warning', 'error',
                                          'critical', 'fatal'])
