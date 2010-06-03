#!/usr/bin/env python
"""Generic config parsing and dumping, the way I remember it from scripts
gone by.

Ideally the config is loaded + mixed with command line options, then locked
during runtime.  The config dump should be loadable and re-runnable for a
duplicate run.
"""

from copy import deepcopy
from optparse import OptionParser
import os
import pprint
import sys
try:
    import json
except:
    import simplejson as json
from Log import SimpleFileLogger, MultiFileLogger



# MozOptionParser {{{1
class MozOptionParser(OptionParser):
    """Very slightly modified optparse.OptionParser, which assumes you know
    all the options you just add_option'ed, which is usually the case.

    However, I wanted to be able to have options defined in various places
    and then figure out the dest for each option (e.g. not -v or --verbose,
    but options.verbose) so I could set those directly in the config.

    The options and parser objects in
        (options, args) = parser.parseArgs()
    don't give an easy way of doing that; dir(options) is pretty ugly and
    I was playing with dict() and str() in ways that made me pretty
    frustrated.

    Adding a self.variables list seems like a fairly innocuous and easy
    way to work around this problem.
    """
    def __init__(self, **kwargs):
        OptionParser.__init__(self, **kwargs)
        self.variables = []

    def add_option(self, *args, **kwargs):
        option = OptionParser.add_option(self, *args, **kwargs)
        if option.dest and option.dest not in self.variables:
            self.variables.append(option.dest)



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
        self.logObj = None
        if config:
            self.setConfig(config)
        elif configFile:
            self.setConfig(self.parseConfigFile(configFile))

    def parseConfigFile(self, fileName):
        """Read a config file and return a dictionary.
        TODO: read subsequent config files once self.config is already
        set, with options to override or drop conflicting config settings.
        TODO: have a config file search path, so we're less inflexible
        about cwd().
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

    def queryVar(self, varName, default=None):
        value = self.queryConfig(varName=varName)
        if not value:
            return default
        else:
            return value

    def setVar(self, varName, value):
        self.debug("Setting %s to %s" % (varName, value))
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

    def parseArgs(self, usage="usage: %prog [options]"):
        """Parse command line arguments in a generic way.
        Return the parser object after adding the basic options, so
        child objects can manipulate it.

        TODO: accept a list of options to add by default, map these onto
        the config, and just return the leftover args.  This is the ideal
        behavior.
        TODO: be able to read the options to add from a config.
        TODO: add more default options.
        """
        parser = MozOptionParser(usage=usage)
        parser.add_option("--logLevel", action="store", type="choice",
                          dest="logLevel", default="info",
                          choices=['debug', 'info', 'warning', 'error',
                                   'critical', 'fatal'],
                          help="Set log level (debug|info|warning|error|critical|fatal)")
        parser.add_option("-q", "--quiet", action="store_false",
                          dest="logToConsole", default=True,
                          help="Don't log to the console")
        parser.add_option("--appendToLog", action="store_true",
                          dest="appendToLog", default=False,
                          help="Append to the log")
        return parser

    """There may be a better way of doing this, but I did this previously...
    """
    def log(self, message, level='info', exitCode=-1):
        if self.logObj:
            return self.logObj.log(message, level=level, exitCode=exitCode)
        if level == 'info':
            print message
        elif level == 'debug':
            print 'DEBUG: %s' % message
        elif level in ('warning', 'error', 'critical'):
            print >> sys.stderr, "%s: %s" % (level.upper(), message)
        elif level == 'fatal':
            print >> sys.stderr, "FATAL: %s" % message
            sys.exit(exitCode)

    def debug(self, message):
        level = self.queryVar('logLevel')
        if not level:
            level = self.queryVar('logLevel')
        if level and level == 'debug':
            self.log(message, level='debug')

    def info(self, message):
        self.log(message, level='info')

    def warning(self, message):
        self.log(message, level='warning')

    def warn(self, message):
        self.log(message, level='warning')

    def error(self, message):
        self.log(message, level='error')

    def critical(self, message):
        self.log(message, level='critical')

    def fatal(self, message, exitCode=-1):
        self.log(message, level='fatal', exitCode=exitCode)



# SimpleConfig {{{1
class SimpleConfig(BaseConfig):
    """Effectively BaseConfig with logging.
    """
    def __init__(self, **kwargs):
        BaseConfig.__init__(self, **kwargs)
        self.parseArgs()
        self.newLogObj()

    def parseArgs(self, usage="usage: %prog [options]"):
        parser = BaseConfig.parseArgs(self, usage=usage)
        parser.add_option("--multiLog", action="store_true",
                          dest="multiLog", default=False,
                          help="Log using MultiFileLogger")
        return parser

    def newLogObj(self):
        logConfig = {"loggerName": 'Simple',
                     "logName": 'simple.log',
                     "logDir": '.',
                     "logLevel": 'info',
                     "logFormat": '%(asctime)s - %(levelname)s - %(message)s',
                     "logToConsole": True,
                     "appendToLog": False,
                    }
        for key in logConfig.keys():
            value = self.queryVar(key)
            if value:
                logConfig[key] = value
        if self.queryVar("multiLog"):
            self.logObj = MultiFileLogger(**logConfig)
        else:
            self.logObj = SimpleFileLogger(**logConfig)



# __main__ {{{1
if __name__ == '__main__':
    obj = SimpleConfig(configFile=os.path.join(sys.path[0], 'configs', 'test',
                       'test.json'))
    obj.setVar('additionalkey', 'additionalvalue')
    obj.setVar('key2', 'value2override')
    obj.dumpConfig()
    if obj.queryVar('key1') != "value1":
        obj.error("key1 isn't value1!")

    obj = ParanoidConfig(configFile=os.path.join(sys.path[0], 'configs',
                         'test', 'test.json'))
    obj.lockConfig()
    try:
        obj.info("This should fail: with a FATAL message")
        obj.setVar('thisShouldFail', 'miserably')
    except:
        obj.info("Yay!")
    else:
        obj.error("Gah. ParanoidConfig is broken.")
    if os.path.exists("simple.log"):
        os.remove("simple.log")
