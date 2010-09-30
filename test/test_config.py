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
        contentDict = self._getJsonConfig()
        for key in contentDict.keys():
            self.assertEqual(contentDict[key], c._config[key])
    
    def testDumpConfig(self):
        c = config.BaseConfig(initial_config_file='test/test.json')
        dumpConfigOutput = c.dumpConfig()
        dumpConfigDict = json.loads(dumpConfigOutput)
        contentDict = self._getJsonConfig()
        for key in contentDict.keys():
            self.assertEqual(contentDict[key], dumpConfigDict[key])
