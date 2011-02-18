import os
import subprocess
import sys
import unittest

try:
    import json
except:
    import simplejson as json

import mozharness.base.config as config

class TestConfig(unittest.TestCase):
    def _get_json_config(self, filename="configs/test/test.json",
                         output='dict'):
        fh = open(filename)
        contents = json.load(fh)
        fh.close()
        if 'output' == 'dict':
            return dict(contents)
        else:
            return contents
    
    def test_config(self):
        c = config.BaseConfig(initial_config_file='test/test.json')
        content_dict = self._get_json_config()
        for key in content_dict.keys():
            self.assertEqual(content_dict[key], c._config[key])
    
    def test_read_only_dict(self):
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

    def test_verify_actions(self):
        c = config.BaseConfig(initial_config_file='test/test.json')
        try:
            c.verify_actions(['not_a_real_action'])
        except:
            pass
        else:
            self.assertEqual(0, 1, msg="verify_actions() didn't die on invalid action")
        c = config.BaseConfig(initial_config_file='test/test.json')
        returned_actions = c.verify_actions(c.all_actions)
        self.assertEqual(c.all_actions, returned_actions,
                         msg="returned actions from verify_actions() changed")

    def test_actions(self):
        all_actions=['a', 'b', 'c', 'd', 'e']
        default_actions = ['b', 'c', 'd']
        c = config.BaseConfig(default_actions=default_actions,
                              all_actions=all_actions,
                              initial_config_file='test/test.json')
        self.assertEqual(default_actions, c.get_actions(),
                         msg="default_actions broken")
        c = config.BaseConfig(default_actions=default_actions,
                              all_actions=all_actions,
                              initial_config_file='test/test.json')
        c.parse_args(args=['foo', '--no-action', 'a'])
        self.assertEqual(default_actions, c.get_actions(),
                         msg="--no-ACTION broken")
        c = config.BaseConfig(default_actions=default_actions,
                              all_actions=all_actions,
                              initial_config_file='test/test.json')
        c.parse_args(args=['foo', '--no-c'])
        self.assertEqual(['b', 'd'], c.get_actions(),
                         msg="--no-ACTION broken")
        c = config.BaseConfig(default_actions=default_actions,
                              all_actions=all_actions,
                              initial_config_file='test/test.json')
        c.parse_args(args=['foo', '--add-action', 'e'])
        self.assertEqual(['b', 'c', 'd', 'e'], c.get_actions(),
                         msg="--add-action ACTION broken")
        c = config.BaseConfig(default_actions=default_actions,
                              all_actions=all_actions,
                              initial_config_file='test/test.json')
        c.parse_args(args=['foo', '--only-a', '--only-e'])
        self.assertEqual(['a', 'e'], c.get_actions(),
                         msg="--only-ACTION broken")
