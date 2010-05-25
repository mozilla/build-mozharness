#!/usr/bin/env python

import pprint
try:
    import json
except:
    import simplejson as json

class BaseConfig(object):
    """Basic config setting/getting.
    Debating whether to be paranoid about this stuff and put it all in
    self._config and forcing everyone to use methods to access it, as I
    did elsewhere to lock down the config during runtime, but that's a
    little heavy handed to go with as the default.
    """
    def __init__(self):
        self.config = {}

    def parseConfigFile(self, fileName):
        """Read a config file as self.config.
        TODO: read subsequent config files once self.config is already
        set, with options to override or drop conflicting config settings.
        """
        fh = open(fileName)
        if fileName.endswith('.json'):
            jsonConfig = json.load(fh)
            print json.dumps(jsonConfig, indent=2)
            self.config = json.dumps(jsonConfig)
        else:
            for line in fh:
                line = line[:-1]
                config.append(line)
                self.config = config
        fh.close()

    def dumpConfig(self, fileName=None):
        """Dump the configuration somewhere, default to STDOUT.
        Be nice to be able to write a .py or .json file according to
        filename.
        """
        pp = pprint(PrettyPrinter(indent=2))
        pp.pprint(self.config)

    def parseArgs(self):
        pass



if __name__ == '__main__':
    obj = BaseConfig()
    obj.parseConfigFile('configs/test/test.json')
    obj.dumpConfig
