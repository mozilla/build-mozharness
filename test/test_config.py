import subprocess
import sys
import unittest

try:
    import json
except:
    import simplejson as json

import config

class TestConfig(unittest.TestCase):
    def testDumpConfig(self):
        c = config.BaseConfig(initial_config_file='test/test.json')
        dumpConfigOutput = c.dumpConfig()
        dumpConfigDict = json.loads(dumpConfigOutput)
        fh = open("configs/test/test.json")
        contents = json.load(fh)
        fh.close()
        contentDict = dict(contents)
        for key in contentDict.keys():
            self.assertEqual(contentDict[key], dumpConfigDict[key])
