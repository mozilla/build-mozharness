import os
import shutil
import subprocess
import sys
import unittest

try:
    import json
except:
    import simplejson as json

import mozharness.base.errors as errors
import mozharness.base.script as script

class TestScript(unittest.TestCase):
    def cleanup(self):
        if os.path.exists('test_logs'):
            shutil.rmtree('test_logs')
        if os.path.exists('test_dir'):
            if os.path.isdir('test_dir'):
                shutil.rmtree('test_dir')
            else:
                os.remove('test_dir')
        for filename in ('localconfig.json', 'localconfig.json.bak'):
            if os.path.exists(filename):
                os.remove(filename)

    def setUp(self):
        self.cleanup()

    def tearDown(self):
        self.cleanup()

    def get_debug_script_obj(self):
        s = script.BaseScript(config={'log_type': 'multi',
                                      'log_level': 'debug'},
                              initial_config_file='test/test.json')
        return s

    def get_noop_script_obj(self):
        s = script.MercurialScript(config={'noop': True},
                                   initial_config_file='test/test.json')
        return s

    def test_mkdir_p(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        s.mkdir_p('test_dir/foo/bar/baz')
        self.assertTrue(os.path.isdir('test_dir/foo/bar/baz'),
                        msg="mkdir_p error")
        s.mkdir_p('test_dir/foo/bar/baz')
        self.assertTrue(os.path.isdir('test_dir/foo/bar/baz'),
                        msg="mkdir_p error when dir exists")

    def test_helper_functions(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        s.mkdir_p('test_dir')
        self.assertTrue(os.path.isdir('test_dir'),
                        msg="mkdir_p error")
        # download file
        s.download_file("http://www.mozilla.com", file_name="test_dir/mozilla",
                        error_level="ignore")
        self.assertTrue(os.path.exists('test_dir/mozilla'),
                        msg="error downloading mozilla.com")
        # verify contents
        contents1 = s.get_output_from_command("cat test_dir/mozilla")
        fh = open("test_dir/mozilla")
        contents2 = fh.read()
        fh.close()
        self.assertEqual(contents1, contents2,
                         msg="get_output_from_command('cat file') differs from fh.read")
        # test run_command('cat FILE')
        self.assertEqual(s.run_command("cat mozilla", cwd="test_dir"), 0,
                         msg="run_command('cat file') did not exit 0")
        # test move
        s.move('test_dir/mozilla', 'test_dir/mozilla2')
        self.assertFalse(os.path.exists('test_dir/mozilla'),
                         msg="test_dir/mozilla still exists after move()")
        self.assertTrue(os.path.exists('test_dir/mozilla2'),
                        msg="test_dir/mozilla2 doesn't exist after move()")
        # test copyfile
        s.copyfile('test_dir/mozilla2', 'test_dir/mozilla')
        self.assertTrue(os.path.exists('test_dir/mozilla'),
                         msg="test_dir/mozilla doesn't exist after copyfile()")
        # test run_command(rm)
        s.run_command("rm test_dir/mozilla test_dir/mozilla2")
        self.assertFalse(os.path.exists('test_dir/mozilla'),
                         msg="run_command('rm file') did not remove file")
        # test rmtree
        s.rmtree('test_dir')
        self.assertFalse(os.path.exists('test_dir'),
                         msg="rmtree unsuccessful")
        # test rmtree on nonexistent dir
        s.rmtree('test_dir')
        self.assertFalse(os.path.exists('test_dir'),
                         msg="2nd rmtree unsuccessful")

    def test_summary(self):
        """I need a log watcher helper function, here and in test_log."""
        s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        info_logsize = os.path.getsize("test_logs/test_info.log")
        self.assertTrue(info_logsize > 0,
                        msg="initial info logfile missing/size 0")
        # verify add_summary increases info log size
        s.add_summary('one')
        info_logsize2 = os.path.getsize("test_logs/test_info.log")
        self.assertTrue(info_logsize < info_logsize2,
                        msg="add_summary() not logged")
        # verify add_summary increases warning log size
        warning_logsize = os.path.getsize("test_logs/test_warning.log")
        s.add_summary('two', level="warning")
        warning_logsize2 = os.path.getsize("test_logs/test_warning.log")
        self.assertTrue(warning_logsize < warning_logsize2,
                        msg="add_summary(level='warning') not logged in warning log")
        info_logsize = os.path.getsize("test_logs/test_info.log")
        warning_logsize = os.path.getsize("test_logs/test_warning.log")
        # verify summary() increases log sizes
        s.summary()
        info_logsize2 = os.path.getsize("test_logs/test_info.log")
        warning_logsize2 = os.path.getsize("test_logs/test_warning.log")
        self.assertTrue(info_logsize < info_logsize2,
                        msg="summary() didn't log to info")
        self.assertTrue(warning_logsize < warning_logsize2,
                        msg="summary() with warning didn't log to warning")

    def test_mercurial(self):
        s = script.MercurialScript(initial_config_file='test/test.json')
        s.mkdir_p('test_dir')
        s.run_command("touch test_dir/tools")
        s.scm_checkout("http://hg.mozilla.org/build/tools",
                      parent_dir="test_dir", clobber=True)
        self.assertTrue(os.path.isdir("test_dir/tools"))
        s.scm_checkout("http://hg.mozilla.org/build/tools",
                      dir_name="test_dir/tools", halt_on_failure=False)

    def test_noop_mkdir_p(self):
        s = self.get_noop_script_obj()
        s.mkdir_p('test_dir/foo/bar/baz')
        self.assertFalse(os.path.exists('test_dir'),
                         msg="mkdir_p noop error")

    def test_noop_mkdir_p(self):
        s = self.get_noop_script_obj()
        s.download_file("http://www.mozilla.com", file_name="test_logs/mozilla.com",
                        error_level="ignore")
        self.assertFalse(os.path.exists('test_logs/mozilla.com'),
                         msg="download_file noop error")

    def test_noop_get_output_from_command(self):
        s = self.get_noop_script_obj()
        contents1 = s.run_command("cat test/test.json", cwd="configs",
                                  return_type="output")
        self.assertEqual(contents1, None,
                         msg="get_output_from_command noop error")

    def test_noop_run_command(self):
        s = self.get_noop_script_obj()
        s.run_command("touch test_logs/foo")
        self.assertFalse(os.path.exists('test_logs/foo'),
                         msg="run_command noop error")

    def test_chdir(self):
        s = self.get_noop_script_obj()
        cwd = os.getcwd()
        s.chdir('test_logs', ignore_if_noop=True)
        self.assertEqual(cwd, os.getcwd(),
                         msg="chdir noop error")
        os.chdir(cwd)
        s.chdir('test_logs')
        self.assertEqual('%s/test_logs' % cwd, os.getcwd(),
                         msg="chdir noop noignore error")
        s.chdir(cwd)

    def testLog(self):
        s = self.get_debug_script_obj()
        s.log_obj=None
        s2 = script.BaseScript(config={'log_type': 'multi'},
                               initial_config_file='test/test.json')
        for obj in (s, s2):
            obj.debug("Testing DEBUG")
            obj.warning("Testing WARNING")
            obj.warn("Testing WARNING 2")
            obj.error("Testing ERROR")
            obj.critical("Testing CRITICAL")
            try:
                obj.fatal("Testing FATAL")
            except SystemExit:
                pass
            else:
                self.assertTrue(False, msg="fatal() didn't SystemExit!")

    def test_run_nonexistent_command(self):
        s = self.get_debug_script_obj()
        s.run_command(command="this_cmd_should_not_exist --help",
                      env={'GARBLE': 'FARG'},
                      error_list=errors.PythonErrorList)
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="command not found error not hit")

    def test_run_command_in_bad_dir(self):
        s = self.get_debug_script_obj()
        s.run_command(command="ls",
                      cwd='/this_dir_should_not_exist',
                      error_list=errors.PythonErrorList)
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="bad dir error not hit")

    def test_get_output_from_command_in_bad_dir(self):
        s = self.get_debug_script_obj()
        output = s.get_output_from_command(command="ls",
                     cwd='/this_dir_should_not_exist')
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="bad dir error not hit")

    def test_get_output_from_command_with_missing_file(self):
        s = self.get_debug_script_obj()
        output = s.get_output_from_command(command="ls /this_file_should_not_exist")
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="bad file error not hit")

    def test_get_output_from_command_with_missing_file(self):
        s = self.get_debug_script_obj()
        s.run_command(command="cat mozharness/base/errors.py",
                      error_list=[{
                       'substr': "error", 'level': "error"
                      },{
                       'regex': ',$', 'level': "ignore",
                      },{
                       'substr': ']$', 'level': "warning",
                      }])
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="error list not working properly")
