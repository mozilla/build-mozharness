import glob
import os
import shutil
import sys
import unittest

MH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

script_dir = os.path.join(MH_DIR, 'scripts')
config_dir = os.path.join(MH_DIR, 'configs', 'b2g_bumper')
sys.path.append(script_dir)

def cleanup():
    if os.path.exists('test_logs'):
        shutil.rmtree('test_logs')

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
                
if __name__ == '__main__':
    unittest.main()
