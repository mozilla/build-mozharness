import gc
import os
import re
import shutil
import subprocess
import sys
import unittest

try:
    import simplejson as json
except ImportError:
    import json

import mozharness.base.errors as errors
import mozharness.base.log as log
from mozharness.base.log import DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, IGNORE
import mozharness.base.script as script

test_string = '''foo
bar
baz'''

class CleanupObj(script.OSMixin, log.LogMixin):
    def __init__(self):
        super(CleanupObj, self).__init__()
        self.log_obj = None
        self.config = {'log_level': ERROR}

def cleanup():
    gc.collect()
    # I'm using MercurialVCS here because that gives me access to
    #
    c = CleanupObj()
    for f in ('test_logs', 'test_dir', 'tmpfile_stdout', 'tmpfile_stderr'):
        c.rmtree(f)

def get_debug_script_obj():
    s = script.BaseScript(config={'log_type': 'multi',
                                  'log_level': DEBUG},
                          initial_config_file='test/test.json')
    return s

def get_noop_script_obj():
    s = script.BaseScript(config={'noop': True},
                          initial_config_file='test/test.json')
    return s

class TestScript(unittest.TestCase):
    def setUp(self):
        cleanup()
        self.s = None

    def tearDown(self):
        if hasattr(self, 's') and isinstance(self.s, object):
            del(self.s)
        cleanup()

    def test_nonexistent_mkdir_p(self):
        self.s = script.BaseScript(initial_config_file='test/test.json')
        self.s.mkdir_p('test_dir/foo/bar/baz')
        self.assertTrue(os.path.isdir('test_dir/foo/bar/baz'),
                        msg="mkdir_p error")

    def test_existing_mkdir_p(self):
        self.s = script.BaseScript(initial_config_file='test/test.json')
        os.makedirs('test_dir/foo/bar/baz')
        self.s.mkdir_p('test_dir/foo/bar/baz')
        self.assertTrue(os.path.isdir('test_dir/foo/bar/baz'),
                        msg="mkdir_p error when dir exists")

    def test_noop_mkdir_p(self):
        self.s = get_noop_script_obj()
        self.s.mkdir_p('test_dir/foo/bar/baz')
        self.assertFalse(os.path.exists('test_dir'),
                         msg="mkdir_p noop error")

    def test_noop_mkdir_p(self):
        self.s = get_noop_script_obj()
        self.s.download_file("http://www.mozilla.com", file_name="test_logs/mozilla.com",
                        error_level=IGNORE)
        self.assertFalse(os.path.exists('test_logs/mozilla.com'),
                         msg="download_file noop error")

    def test_noop_get_output_from_command(self):
        self.s = get_noop_script_obj()
        contents1 = self.s.get_output_from_command("cat test/test.json", cwd="configs")
        self.assertEqual(contents1, '',
                         msg="get_output_from_command noop error")

    def test_noop_run_command(self):
        self.s = get_noop_script_obj()
        self.s.run_command("touch test_logs/foo")
        self.assertFalse(os.path.exists('test_logs/foo'),
                         msg="run_command noop error")

    def test_chdir(self):
        self.s = get_noop_script_obj()
        cwd = os.getcwd()
        self.s.chdir('test_logs', ignore_if_noop=True)
        self.assertEqual(cwd, os.getcwd(),
                         msg="chdir noop error")
        os.chdir(cwd)
        self.s.chdir('test_logs')
        self.assertEqual(os.path.join(cwd, "test_logs"), os.getcwd(),
                         msg="chdir noop noignore error")
        self.s.chdir(cwd)

    def _test_log_helper(self, obj):
        obj.debug("Testing DEBUG")
        obj.warning("Testing WARNING")
        obj.error("Testing ERROR")
        obj.critical("Testing CRITICAL")
        try:
            obj.fatal("Testing FATAL")
        except SystemExit:
            pass
        else:
            self.assertTrue(False, msg="fatal() didn't SystemExit!")

    def test_log(self):
        self.s = get_debug_script_obj()
        self.s.log_obj=None
        self._test_log_helper(self.s)
        del(self.s)
        self.s = script.BaseScript(initial_config_file='test/test.json')
        self._test_log_helper(self.s)

    def test_run_nonexistent_command(self):
        self.s = get_debug_script_obj()
        self.s.run_command(command="this_cmd_should_not_exist --help",
                      env={'GARBLE': 'FARG'},
                      error_list=errors.PythonErrorList)
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="command not found error not hit")

    def test_run_command_in_bad_dir(self):
        self.s = get_debug_script_obj()
        self.s.run_command(command="ls",
                      cwd='/this_dir_should_not_exist',
                      error_list=errors.PythonErrorList)
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="bad dir error not hit")

    def test_get_output_from_command_in_bad_dir(self):
        self.s = get_debug_script_obj()
        output = self.s.get_output_from_command(command="ls",
                     cwd='/this_dir_should_not_exist')
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="bad dir error not hit")

    def test_get_output_from_command_with_missing_file(self):
        self.s = get_debug_script_obj()
        output = self.s.get_output_from_command(command="ls /this_file_should_not_exist")
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="bad file error not hit")

    def test_get_output_from_command_with_missing_file(self):
        self.s = get_debug_script_obj()
        self.s.run_command(command="cat mozharness/base/errors.py",
                      error_list=[{
                       'substr': "error", 'level': ERROR
                      },{
                       'regex': re.compile(',$'), 'level': IGNORE,
                      },{
                       'substr': ']$', 'level': WARNING,
                      }])
        error_logsize = os.path.getsize("test_logs/test_error.log")
        self.assertTrue(error_logsize > 0,
                        msg="error list not working properly")



class TestHelperFunctions(unittest.TestCase):
    temp_file = "test_dir/mozilla"
    def setUp(self):
        cleanup()
        self.s = None

    def tearDown(self):
        if hasattr(self, 's') and isinstance(self.s, object):
            del(self.s)
        cleanup()

    def _create_temp_file(self, contents=test_string):
        os.mkdir('test_dir')
        fh = open(self.temp_file, "w+")
        fh.write(contents)
        fh.close

    def test_mkdir_p(self):
        self.s = script.BaseScript(initial_config_file='test/test.json')
        self.s.mkdir_p('test_dir')
        self.assertTrue(os.path.isdir('test_dir'),
                        msg="mkdir_p error")

    def test_get_output_from_command(self):
        self._create_temp_file()
        self.s = script.BaseScript(initial_config_file='test/test.json')
        contents = self.s.get_output_from_command("cat %s" % self.temp_file)
        del(self.s)
        self.assertEqual(test_string, contents,
                         msg="get_output_from_command('cat file') differs from fh.write")

    def test_run_command(self):
        self._create_temp_file()
        self.s = script.BaseScript(initial_config_file='test/test.json')
        temp_file_name = os.path.basename(self.temp_file)
        self.assertEqual(self.s.run_command("cat %s" % temp_file_name,
                                       cwd="test_dir"), 0,
                         msg="run_command('cat file') did not exit 0")

    def test_move1(self):
        self._create_temp_file()
        self.s = script.BaseScript(initial_config_file='test/test.json')
        temp_file2 = '%s2' % self.temp_file
        self.s.move(self.temp_file, temp_file2)
        self.assertFalse(os.path.exists(self.temp_file),
                         msg="%s still exists after move()" % self.temp_file)

    def test_move2(self):
        self._create_temp_file()
        self.s = script.BaseScript(initial_config_file='test/test.json')
        temp_file2 = '%s2' % self.temp_file
        self.s.move(self.temp_file, temp_file2)
        self.assertTrue(os.path.exists(temp_file2),
                        msg="%s doesn't exist after move()" % temp_file2)

    def test_copyfile(self):
        self._create_temp_file()
        self.s = script.BaseScript(initial_config_file='test/test.json')
        temp_file2 = '%s2' % self.temp_file
        self.s.copyfile(self.temp_file, temp_file2)
        self.assertEqual(os.path.getsize(self.temp_file),
                         os.path.getsize(temp_file2),
                         msg="%s and %s are different sizes after copyfile()" % \
                             (self.temp_file, temp_file2))

    def test_existing_rmtree(self):
        self._create_temp_file()
        self.s = script.BaseScript(initial_config_file='test/test.json')
        self.s.mkdir_p('test_dir/foo/bar/baz')
        self.s.rmtree('test_dir')
        self.assertFalse(os.path.exists('test_dir'),
                         msg="rmtree unsuccessful")

    def test_nonexistent_rmtree(self):
        self.s = script.BaseScript(initial_config_file='test/test.json')
        status = self.s.rmtree('test_dir')
        self.assertFalse(status, msg="nonexistent rmtree error")

    def test_existing_rmdir_recursive(self):
        self._create_temp_file()
        self.s = script.BaseScript(initial_config_file='test/test.json')
        self.s.mkdir_p('test_dir/foo/bar/baz')
        self.s._rmdir_recursive('test_dir')
        self.assertFalse(os.path.exists('test_dir'),
                         msg="_rmdir_recursive unsuccessful")

    def test_chmod(self):
        self._create_temp_file()
        self.s = script.BaseScript(initial_config_file='test/test.json')
        if not self.s._is_windows():
            self.s.chmod(self.temp_file, 0100700)
            self.assertEqual(os.stat(self.temp_file)[0], 33216,
                             msg="chmod unsuccessful")

    def test_env_normal(self):
        self.s = script.BaseScript(initial_config_file='test/test.json')
        script_env = self.s.query_env()
        self.assertEqual(script_env, os.environ,
                         msg="query_env() != env\n%s\n%s" % (script_env, os.environ))

    def test_env_normal2(self):
        self.s = script.BaseScript(initial_config_file='test/test.json')
        self.s.query_env()
        script_env = self.s.query_env()
        self.assertEqual(script_env, os.environ,
                         msg="Second query_env() != env\n%s\n%s" % (script_env, os.environ))

    def test_env_partial(self):
        self.s = script.BaseScript(initial_config_file='test/test.json')
        script_env = self.s.query_env(partial_env={'foo': 'bar'})
        self.assertTrue('foo' in script_env and script_env['foo'] == 'bar')

    def test_env_path(self):
        self.s = script.BaseScript(initial_config_file='test/test.json')
        partial_path = "yaddayadda:%(PATH)s"
        full_path = partial_path % {'PATH': os.environ['PATH']}
        script_env = self.s.query_env(partial_env={'PATH': partial_path})
        self.assertEqual(script_env['PATH'], full_path)



class TestScriptLogging(unittest.TestCase):
    # I need a log watcher helper function, here and in test_log.
    def setUp(self):
        cleanup()
        self.s = None

    def tearDown(self):
        if hasattr(self, 's') and isinstance(self.s, object):
            del(self.s)
        cleanup()

    def test_info_logsize(self):
        self.s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        info_logsize = os.path.getsize("test_logs/test_info.log")
        self.assertTrue(info_logsize > 0,
                        msg="initial info logfile missing/size 0")

    def test_add_summary_info(self):
        self.s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        info_logsize = os.path.getsize("test_logs/test_info.log")
        self.s.add_summary('one')
        info_logsize2 = os.path.getsize("test_logs/test_info.log")
        self.assertTrue(info_logsize < info_logsize2,
                        msg="add_summary() info not logged")

    def test_add_summary_warning(self):
        self.s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        warning_logsize = os.path.getsize("test_logs/test_warning.log")
        self.s.add_summary('two', level=WARNING)
        warning_logsize2 = os.path.getsize("test_logs/test_warning.log")
        self.assertTrue(warning_logsize < warning_logsize2,
                        msg="add_summary(level=%s) not logged in warning log" % WARNING)

    def test_summary(self):
        self.s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        self.s.add_summary('one')
        self.s.add_summary('two', level=WARNING)
        info_logsize = os.path.getsize("test_logs/test_info.log")
        warning_logsize = os.path.getsize("test_logs/test_warning.log")
        self.s.summary()
        info_logsize2 = os.path.getsize("test_logs/test_info.log")
        warning_logsize2 = os.path.getsize("test_logs/test_warning.log")
        msg = ""
        if info_logsize >= info_logsize2:
            msg += "summary() didn't log to info!\n"
        if warning_logsize >= warning_logsize2:
            msg += "summary() didn't log to warning!\n"
        self.assertEqual(msg, "", msg=msg)

    def _test_log_level(self, log_level, log_level_file_list):
        self.s = script.BaseScript(config={'log_type': 'multi'},
                              initial_config_file='test/test.json')
        if log_level != FATAL:
            self.s.log('testing', level=log_level)
        else:
            try:
                self.s.fatal('testing')
            except SystemExit:
                pass
        del(self.s)
        msg = ""
        for level in log_level_file_list:
            log_path = "test_logs/test_%s.log" % level
            if not os.path.exists(log_path):
                msg += "%s doesn't exist!\n" % log_path
            else:
                filesize = os.path.getsize(log_path)
                if not filesize > 0:
                    msg += "%s is size 0!\n" % log_path
        self.assertEqual(msg, "", msg=msg)

    def test_debug(self):
        self._test_log_level(DEBUG, [])

    def test_ignore(self):
        self._test_log_level(IGNORE, [])

    def test_info(self):
        self._test_log_level(INFO, [INFO])

    def test_warning(self):
        self._test_log_level(WARNING, [INFO, WARNING])

    def test_error(self):
        self._test_log_level(ERROR, [INFO, WARNING, ERROR])

    def test_critical(self):
        self._test_log_level(CRITICAL, [INFO, WARNING, ERROR, CRITICAL])

    def test_fatal(self):
        self._test_log_level(FATAL, [INFO, WARNING, ERROR, CRITICAL, FATAL])

if __name__ == '__main__':
    unittest.main()
