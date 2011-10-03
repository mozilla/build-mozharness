import os
import shutil
import unittest

import mozharness.base.script as script
from mozharness.base.log import DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, IGNORE

def cleanup():
    for f in ('test_logs', 'test_dir', 'tmpfile_stdout', 'tmpfile_stderr'):
        if os.path.exists(f):
            if os.path.isdir(f):
                shutil.rmtree(f)
            else:
                os.remove(f)

class TestNetworkedHelperFunctions(unittest.TestCase):
    temp_file = "test_dir/mozilla"
    def setUp(self):
        cleanup()

    def tearDown(self):
        cleanup()

    def test_download_file(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        os.mkdir('test_dir')
        s.download_file("http://www.mozilla.com", file_name=self.temp_file,
                        error_level=IGNORE)
        self.assertTrue(os.path.exists(self.temp_file),
                        msg="error downloading mozilla.com")

    def test_download_bad_domain(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        os.mkdir('test_dir')
        self.assertRaises(SystemExit, s.download_file,
                          "http://www.mozilla.sdfsdsdf",
                          error_level=FATAL)

    def test_download_bad_file(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        os.mkdir('test_dir')
        self.assertRaises(SystemExit, s.download_file,
                          "http://www.google.com/lsdkfjlsdkfjekisdilsj",
                          error_level=FATAL)
