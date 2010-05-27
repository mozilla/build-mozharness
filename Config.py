#!/usr/bin/env python

from copy import deepcopy
import os
import pprint
import sys
try:
    import json
except:
    import simplejson as json



# BaseConfig {{{1
class BaseConfig(object):
    """Basic config setting/getting.
    Debating whether to be paranoid about this stuff and put it all in
    self._config and forcing everyone to use methods to access it, as I
    did elsewhere to lock down the config during runtime, but that's a
    little heavy handed to go with as the default.
    """
    def __init__(self, config=None, configFile=None):
        self.config = {}
        if config:
            self.setConfig(config)
        elif configFile:
            self.setConfig(self.parseConfigFile(configFile))

    def parseConfigFile(self, fileName):
        """Read a config file and return a dictionary.
        TODO: read subsequent config files once self.config is already
        set, with options to override or drop conflicting config settings.
        """
        fh = open(fileName)
        config = {}
        if fileName.endswith('.json'):
            jsonConfig = json.load(fh)
            config = dict(jsonConfig)
        else:
            contents = []
            for line in fh:
                line = line[:-1]
                contents.append(line)
                config = dict(contents)
        fh.close()

        """Return it here? Or set something?
        """
        return config

    def mapConfig(self, config1, config2):
        """Copy key/value pairs of config2 onto config1.
        There can be a lot of other behaviors here; writing this one first.
        """
        config = deepcopy(config1)
        for key, value in config2.iteritems():
            config[key] = value
        return config

    def queryConfig(self, varName=None):
        if not varName:
            return self.config
        try:
            str(varName) == varName
        except:
            """It would be cool to allow for dictionaries here, to specify
            which subset(s) of config to return
            """
            pass
        else:
            if varName in self.config:
                return self.config[varName]

    def setConfig(self, config, overwrite=False):
        """It would be good to detect if self.config is already set, and
        if so, have settings as to how to determine what overrides what.
        """
        if self.config and not overwrite:
            self.config = self.mapConfig(self.config, config)
        else:
            self.config = config

    def queryVar(self, varName):
        return self.queryConfig(varName=varName)

    def setVar(self, varName, value):
        self.config[varName] = value

    def dumpConfig(self, config=None, fileName=None):
        """Dump the configuration somewhere, default to STDOUT.
        Be nice to be able to write a .py or .json file according to
        filename.
        """
        if not config:
            config = self.queryConfig()
        if not fileName:
            pp = pprint.PrettyPrinter(indent=2, width=10)
            return pp.pformat(config)

    def parseArgs(self):
        pass



class SimpleConfig(BaseConfig):
    def __init__(self, **kwargs):
        BaseConfig.__init__(self, **kwargs)




# ParanoidConfig {{{1
class ParanoidConfig(BaseConfig):
    def __init__(self, **kwargs):
        self._config = {}
        self._configLock = False
        BaseConfig.__init__(self, **kwargs)

    def lockConfig(self):
        self._configLock = True

    def _checkConfigLock(self):
        if self._configLock:
            print "FATAL: ParanoidConfig is locked! Exiting..."
            sys.exit(-1)

    def queryConfig(self, varName=None):
        if not varName:
            return self._config
        try:
            str(varName) == varName
        except:
            """It would be cool to allow for dictionaries here, to specify
            which subset(s) of config to return
            """
            pass
        else:
            if varName in self._config:
                return self._config[varName]

    def setConfig(self, config, overwrite=False):
        self._checkConfigLock()
        if self._config and not overwrite:
            self._config = self.mapConfig(self._config, config)
        else:
            self._config = config

    def setVar(self, varName, value):
        self._checkConfigLock()
        self._config[varName] = value



# __main__ {{{1
if __name__ == '__main__':
    obj = BaseConfig(configFile=os.path.join(sys.path[0], 'configs', 'test',
                     'test.json'))
    obj.setVar('additionalkey', 'additionalvalue')
    obj.setVar('key2', 'value2override')
    obj.dumpConfig()
    if obj.queryVar('key1') != "value1":
        print "ERROR key1 isn't value1!"

    obj = ParanoidConfig(configFile=os.path.join(sys.path[0], 'configs',
                         'test', 'test.json'))
    obj.lockConfig()
    try:
        print "This should fail: with a FATAL message"
        obj.setVar('thisShouldFail', 'miserably')
    except:
        print "Yay!"
    else:
        print "Gah. ParanoidConfig is broken."
