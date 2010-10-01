import pprint
import subprocess
import sys
import unittest

try:
    import json
except:
    import simplejson as json

import config

class TestConfig(unittest.TestCase):
    def _getJsonConfig(self, filename="configs/test/test.json",
                       output='dict'):
        fh = open(filename)
        contents = json.load(fh)
        fh.close()
        if 'output' == 'dict':
            return dict(contents)
        else:
            return contents
    
    def testConfig(self):
        c = config.BaseConfig(initial_config_file='test/test.json')
        content_dict = self._getJsonConfig()
        for key in content_dict.keys():
            self.assertEqual(content_dict[key], c._config[key])
    
    def testDumpConfig(self):
        c = config.BaseConfig(initial_config_file='test/test.json')
        dump_config_output = c.dumpConfig()
        dump_config_dict = json.loads(dump_config_output)
        content_dict = self._getJsonConfig()
        for key in content_dict.keys():
            self.assertEqual(content_dict[key], dump_config_dict[key])

    def testReadOnlyDict(self):
        # ReadOnlyDict {{{
        control_dict = {
         'b':'2',
         'c':{'d': '4'},
         'e':['f', 'g'],
        }
        r = config.ReadOnlyDict(control_dict)
        self.assertEqual(r, control_dict,
                             msg="can't transfer dict to ReadOnlyDict")
        r.popitem()
        self.assertEqual(len(r), len(control_dict) - 1,
                         msg="can't popitem() ReadOnlyDict when unlocked")
        r = config.ReadOnlyDict(control_dict)
        r.pop('e')
        self.assertEqual(len(r), len(control_dict) - 1,
                         msg="can't pop() ReadOnlyDict when unlocked")
        r = config.ReadOnlyDict(control_dict)
        r['e'] = 'yarrr'
        self.assertEqual(r['e'], 'yarrr',
                         msg="can't set var in ReadOnlyDict when unlocked")
        del r['e']
        self.assertEqual(len(r), len(control_dict) - 1,
                         msg="can't del in ReadOnlyDict when unlocked")
        r.clear()
        self.assertEqual(r, {},
                             msg="can't clear() ReadOnlyDict when unlocked")
        for key in control_dict.keys():
            r.setdefault(key, control_dict[key])
        self.assertEqual(r, control_dict,
                             msg="can't setdefault() ReadOnlyDict when unlocked")
        r = config.ReadOnlyDict(control_dict)
        r.lock()
        # TODO use |with self.assertRaises(AssertionError):| if/when we're
        # all on 2.7.
        try:
            r['e'] = 2
        except:
            pass
        else:
            self.assertEqual(0, 1, msg="can set r['e'] when locked")
        try:
            del r['e']
        except:
            pass
        else:
            self.assertEqual(0, 1, "can del r['e'] when locked")
        self.assertRaises(AssertionError, r.popitem)
        self.assertRaises(AssertionError, r.update, {})
        self.assertRaises(AssertionError, r.setdefault, {})
        self.assertRaises(AssertionError, r.pop)
        self.assertRaises(AssertionError, r.clear)
        # End ReadOnlyDict }}}

    def testVerifyActions(self):
        c = config.BaseConfig(initial_config_file='test/test.json')
        c.dumpConfig()
        try:
            c.verifyActions(['not_a_real_action'])
        except:
            pass
        else:
            self.assertIsNotNone(None, msg="verifyActions() didn't die on invalid action")
        c = config.BaseConfig(initial_config_file='test/test.json')
        returned_actions = c.verifyActions(c.all_actions)
        self.assertEqual(c.all_actions, returned_actions,
                         msg="returned actions from verifyActions() changed")

    def testActions(self):
        all_actions=['a', 'b', 'c', 'd', 'e']
        default_actions = ['b', 'c', 'd']
        c = config.BaseConfig(default_actions=default_actions,
                              all_actions=all_actions,
                              initial_config_file='test/test.json')
        self.assertEqual(default_actions, c.getActions(),
                         msg="default_actions broken")
        c = config.BaseConfig(default_actions=default_actions,
                              all_actions=all_actions,
                              initial_config_file='test/test.json')
        c.parseArgs(args=['foo', '--no-c'])
        self.assertEqual(['b', 'd'], c.getActions(),
                         msg="--no-ACTION broken")
        c = config.BaseConfig(default_actions=default_actions,
                              all_actions=all_actions,
                              initial_config_file='test/test.json')
        c.parseArgs(args=['foo', '--add-action', 'e'])
        self.assertEqual(['b', 'c', 'd', 'e'], c.getActions(),
                         msg="--add-action ACTION broken")
        c = config.BaseConfig(default_actions=default_actions,
                              all_actions=all_actions,
                              initial_config_file='test/test.json')
        c.parseArgs(args=['foo', '--only-a', '--only-e'])
        self.assertEqual(['a', 'e'], c.getActions(),
                         msg="--only-ACTION broken")
