import glob
import os
import shutil
import subprocess
import sys
import unittest

import mozharness.base.log as log
import mozharness.base.script as script

MH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

script_dir = os.path.join(MH_DIR, 'scripts', 'vcs-sync')
config_dir = os.path.join(MH_DIR, 'configs', 'vcs_sync')
sys.path.append(script_dir)
import vcs_sync

def cleanup():
    if os.path.exists('test_logs'):
        shutil.rmtree('test_logs')

def _write_data_file(fname, *args):
    nl = '\n' if args[0][-1] != '\n' else ''
    with open(fname, 'wt') as df:
        df.writelines(nl.join(args))
        df.writelines(nl)

class TestVCSSync(unittest.TestCase):
    def setUp(self):
        cleanup()

    def tearDown(self):
        cleanup()

    def test_config_files_load(self):
        # assume every .py file is legit configuration that can be
        # imported. Since file name may not be module name, do it via
        # system
        configs_with_error = []
        for f in glob.iglob(os.path.join(config_dir, '*.py')):
            junk = {}
            try:
                execfile(f, junk)
            except Exception as e:
                # we don't car about KeyErrors, as we may not have a
                # proper environment
                if not isinstance(e, KeyError):
                    configs_with_error.append('%s: <%s>%s' % (f,
                        type(e), e.message))
        if len(configs_with_error):
            self.fail("Bad configs: %s" % (', '.join(configs_with_error)))
                
    def _pull_out_new_sha_lookups_multiple(self):
        # HACK: test below never finished or checked in, keep for
        # history, but don't execute
        converter = vcs_sync.HgGitScript(require_config_file=False)
        old_file = '/tmp/hwine/old_file'
        new_file = '/tmp/hwine/new_file'
        expected_diff = '/tmp/hwine/expected_diff'
        diff_file = '/tmp/hwine/diff_file'
        _write_data_file(old_file, '1 1', '3 3', '5 5')
        _write_data_file(new_file, '1 1', '2 2', '3 3',
                '4 4', '5 5', '6 6')
        os.system("comm -13 %s %s > %s" % (old_file, new_file,
            expected_diff))
        diff = converter.pull_out_new_sha_lookups(old_file, new_file)
        _write_data_file(diff_file, *diff)
        ec = os.system('cmp %s %s' % (diff_file, expected_diff))
        self.assertEquals(ec, 0)

    def _pull_out_new_sha_lookups_single(self):
        # HACK: test below never finished or checked in, keep for
        # history, but don't execute
        converter = vcs_sync.HgGitScript(require_config_file=False)
        old_file = '/tmp/hwine/old_file'
        new_file = '/tmp/hwine/new_file'
        expected_diff = '/tmp/hwine/expected_diff'
        diff_file = '/tmp/hwine/diff_file'
        _write_data_file(old_file, '1 1', '3 3', '5 5')
        _write_data_file(new_file, '1 1', '2 2', '3 3', '5 5')
        os.system("comm -13 %s %s > %s" % (old_file, new_file,
            expected_diff))
        diff = converter.pull_out_new_sha_lookups(old_file, new_file)
        _write_data_file(diff_file, *diff)
        ec = os.system('cmp %s %s' % (diff_file, expected_diff))
        self.assertEquals(ec, 0)



if __name__ == '__main__':
    unittest.main()
