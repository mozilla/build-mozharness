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

test_string = '''foo
bar
baz'''

def cleanup():
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

def get_debug_script_obj():
    s = script.BaseScript(config={'log_type': 'multi',
                                  'log_level': 'debug'},
                          initial_config_file='test/test.json')
    return s

def get_noop_script_obj():
    s = script.MercurialScript(config={'noop': True},
                               initial_config_file='test/test.json')
    return s

class TestScript(unittest.TestCase):
    def setUp(self):
        cleanup()

    def tearDown(self):
        cleanup()

    def test_nonexistent_mkdir_p(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        s.mkdir_p('test_dir/foo/bar/baz')
        self.assertTrue(os.path.isdir('test_dir/foo/bar/baz'),
                        msg="mkdir_p error")

    def test_existing_mkdir_p(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        os.makedirs('test_dir/foo/bar/baz')
        s.mkdir_p('test_dir/foo/bar/baz')
        self.assertTrue(os.path.isdir('test_dir/foo/bar/baz'),
                        msg="mkdir_p error when dir exists")

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
        s = get_noop_script_obj()
        s.mkdir_p('test_dir/foo/bar/baz')
        self.assertFalse(os.path.exists('test_dir'),
                         msg="mkdir_p noop error")

    def test_noop_mkdir_p(self):
        s = get_noop_script_obj()
        s.download_file("http://www.mozilla.com", file_name="test_logs/mozilla.com",
                        error_level="ignore")
        self.assertFalse(os.path.exists('test_logs/mozilla.com'),
                         msg="download_file noop error")

    def test_noop_get_output_from_command(self):
        s = get_noop_script_obj()
        contents1 = s.run_command("cat test/test.json", cwd="configs",
                                  return_type="output")
        self.assertEqual(contents1, None,
                         msg="get_output_from_command noop error")

    def test_noop_run_command(self):
        s = get_noop_script_obj()
        s.run_command("touch test_logs/foo")
        self.assertFalse(os.path.exists('test_logs/foo'),
                         msg="run_command noop error")

    def test_chdir(self):
        s = get_noop_script_obj()
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
        s = get_debug_script_obj()
        s.log_obj=None
        s2 = script.BaseScript(initial_config_file='test/test.json')
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
        s = get_debug_script_obj()
        s.run_command(command="this_cmd_should_not_exist --help",
                      env={'GARBLE': 'FARG'},
                      error_list=errors.PythonErrorList)
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="command not found error not hit")

    def test_run_command_in_bad_dir(self):
        s = get_debug_script_obj()
        s.run_command(command="ls",
                      cwd='/this_dir_should_not_exist',
                      error_list=errors.PythonErrorList)
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="bad dir error not hit")

    def test_get_output_from_command_in_bad_dir(self):
        s = get_debug_script_obj()
        output = s.get_output_from_command(command="ls",
                     cwd='/this_dir_should_not_exist')
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="bad dir error not hit")

    def test_get_output_from_command_with_missing_file(self):
        s = get_debug_script_obj()
        output = s.get_output_from_command(command="ls /this_file_should_not_exist")
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="bad file error not hit")

    def test_get_output_from_command_with_missing_file(self):
        s = get_debug_script_obj()
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



class TestHelperFunctions(unittest.TestCase):
    temp_file = "test_dir/mozilla"
    def setUp(self):
        cleanup()

    def tearDown(self):
        cleanup()

    def _create_temp_file(self):
        os.mkdir('test_dir')
        fh = open(self.temp_file, "w+")
        fh.write(test_string)
        fh.close

    def test_mkdir_p(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        s.mkdir_p('test_dir')
        self.assertTrue(os.path.isdir('test_dir'),
                        msg="mkdir_p error")

    def test_download_file(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        os.mkdir('test_dir')
        s.download_file("http://www.mozilla.com", file_name=self.temp_file,
                        error_level="ignore")
        self.assertTrue(os.path.exists(self.temp_file),
                        msg="error downloading mozilla.com")

    def test_get_output_from_command(self):
        self._create_temp_file()
        s = script.BaseScript(initial_config_file='test/test.json')
        contents = s.get_output_from_command("cat %s" % self.temp_file)
        self.assertEqual(test_string, contents,
                         msg="get_output_from_command('cat file') differs from fh.write")

    def test_run_command(self):
        self._create_temp_file()
        s = script.BaseScript(initial_config_file='test/test.json')
        temp_file_name = os.path.basename(self.temp_file)
        self.assertEqual(s.run_command("cat %s" % temp_file_name,
                                       cwd="test_dir"), 0,
                         msg="run_command('cat file') did not exit 0")

    def test_move1(self):
        self._create_temp_file()
        s = script.BaseScript(initial_config_file='test/test.json')
        temp_file2 = '%s2' % self.temp_file
        s.move(self.temp_file, temp_file2)
        self.assertFalse(os.path.exists(self.temp_file),
                         msg="%s still exists after move()" % self.temp_file)

    def test_move2(self):
        self._create_temp_file()
        s = script.BaseScript(initial_config_file='test/test.json')
        temp_file2 = '%s2' % self.temp_file
        s.move(self.temp_file, temp_file2)
        self.assertTrue(os.path.exists(temp_file2),
                        msg="%s doesn't exist after move()" % temp_file2)

    def test_copyfile(self):
        self._create_temp_file()
        s = script.BaseScript(initial_config_file='test/test.json')
        temp_file2 = '%s2' % self.temp_file
        s.copyfile(self.temp_file, temp_file2)
        self.assertEqual(os.path.getsize(self.temp_file),
                         os.path.getsize(temp_file2),
                         msg="%s and %s are different sizes after copyfile()" % \
                             (self.temp_file, temp_file2))

    def test_existing_rmtree(self):
        self._create_temp_file()
        s = script.BaseScript(initial_config_file='test/test.json')
        s.rmtree('test_dir')
        self.assertFalse(os.path.exists('test_dir'),
                         msg="rmtree unsuccessful")

    def test_nonexistent_rmtree(self):
        s = script.BaseScript(initial_config_file='test/test.json')
        status = s.rmtree('test_dir')
        self.assertFalse(status, msg="nonexistent rmtree error")



class TestSummary(unittest.TestCase):
    # I need a log watcher helper function, here and in test_log.
    def setUp(self):
        cleanup()

    def tearDown(self):
        cleanup()

    def test_info_logsize(self):
        s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        info_logsize = os.path.getsize("test_logs/test_info.log")
        self.assertTrue(info_logsize > 0,
                        msg="initial info logfile missing/size 0")

    def test_add_summary_info(self):
        s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        info_logsize = os.path.getsize("test_logs/test_info.log")
        s.add_summary('one')
        info_logsize2 = os.path.getsize("test_logs/test_info.log")
        self.assertTrue(info_logsize < info_logsize2,
                        msg="add_summary() info not logged")

    def test_add_summary_warning(self):
        s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        warning_logsize = os.path.getsize("test_logs/test_warning.log")
        s.add_summary('two', level="warning")
        warning_logsize2 = os.path.getsize("test_logs/test_warning.log")
        self.assertTrue(warning_logsize < warning_logsize2,
                        msg="add_summary(level='warning') not logged in warning log")

    def test_summary(self):
        s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        s.add_summary('one')
        s.add_summary('two', level="warning")
        info_logsize = os.path.getsize("test_logs/test_info.log")
        warning_logsize = os.path.getsize("test_logs/test_warning.log")
        s.summary()
        info_logsize2 = os.path.getsize("test_logs/test_info.log")
        warning_logsize2 = os.path.getsize("test_logs/test_warning.log")
        msg = ""
        if info_logsize >= info_logsize2:
            msg += "summary() didn't log to info!\n"
        if warning_logsize >= warning_logsize2:
            msg += "summary() didn't log to warning!\n"
        self.assertEqual(msg, "", msg=msg)
