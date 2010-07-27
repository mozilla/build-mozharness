#!/usr/bin/env python
"""Generic config parsing and dumping, the way I remember it from scripts
gone by.

Ideally the config is loaded + mixed with command line options, then locked
during runtime.  The config dump should be loadable and re-runnable for a
duplicate run.

TODO:

* dumpConfig and loadConfig need to be seamless. And written.
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
from Log import SimpleFileLogger, MultiFileLogger, BasicFunctions



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
    way to work around this problem

    appendVariables is a small hack to allow for things like
        ./script --locale en-US,multi --locale fr
    in which case we get
        locales=["en-US,multi", "fr"]
    If we then say
        locales = ','.join(locales).split(',')
    then we get
        locales=["en-US", "multi", "fr"]
    which is nice for less commandline typing.
    """
    def __init__(self, **kwargs):
        OptionParser.__init__(self, **kwargs)
        self.variables = []
        self.appendVariables = []

    def add_option(self, *args, **kwargs):
        origAction = kwargs['action']
        if origAction.endswith("_split"):
            kwargs['action'] = kwargs['action'].replace("_split", "")
        if origAction.startswith("temp_"):
            kwargs['action'] = kwargs['action'].replace("temp_", "")
        option = OptionParser.add_option(self, *args,
                                         **kwargs)
        if option.dest and option.dest not in self.variables:
            if not origAction.startswith("temp_"):
                self.variables.append(option.dest)
            if origAction.endswith("_split"):
                self.appendVariables.append(option.dest)



# BaseConfig {{{1
class BaseConfig(object):
    """Basic config setting/getting.
    Debating whether to be paranoid about this stuff and put it all in
    self._config+rand(10000) and forcing everyone to use methods to access
    it, as I did elsewhere to lock down the config during runtime, but
    that's a little heavy handed to go with as the default.
    """
    def __init__(self, config=None, initialConfigFile=None, configOptions=[],
                 allActions=["clobber", "build"], defaultActions=None,
                 requireConfigFile=False, usage="usage: %prog [options]"):
        self._config = {}
        self.actions = []
        self.logObj = None
        self.configLock = False
        self.requireConfigFile = requireConfigFile

        self.allActions = allActions
        if defaultActions:
            self.defaultActions = defaultActions
        else:
            self.defaultActions = allActions

        if config:
            self.setConfig(config)
        if initialConfigFile:
            self.setConfig(self.parseConfigFile(initialConfigFile))
        self._createConfigParser(configOptions, usage)
        self.parseArgs()

    def _createConfigParser(self, configOptions, usage):
        self.configParser = MozOptionParser(usage=usage)
        self.configParser.add_option(
         "--logLevel", action="store",
         type="choice", dest="logLevel", default="info",
         choices=['debug', 'info', 'warning', 'error', 'critical', 'fatal'],
         help="Set log level (debug|info|warning|error|critical|fatal)"
        )
        self.configParser.add_option(
         "-q", "--quiet", action="store_false", dest="logToConsole",
         default=True, help="Don't log to the console"
        )
        self.configParser.add_option(
         "--appendToLog", action="store_true",
         dest="appendToLog", default=False,
         help="Append to the log"
        )
        self.configParser.add_option(
         "--workDir", action="store", dest="workDir",
         type="string", default="workDir",
         help="Specify the workDir (subdir of baseWorkDir)"
        )
        self.configParser.add_option(
         "--baseWorkDir", action="store", dest="baseWorkDir",
         type="string", default=os.getcwd(),
         help="Specify the absolute path of the parent of the working directory"
        )
        self.configParser.add_option(
         "--configFile", action="store", dest="configFile",
         type="string", help="Specify the config file (required)"
        )

        # Actions
        self.configParser.add_option(
         "--action", action="temp_append_split",
         dest="onlyActions", metavar="ACTIONS",
         help="Do action %s" % self.allActions
        )
        self.configParser.add_option(
         "--addAction", action="temp_append_split",
         dest="addActions", metavar="ACTIONS",
         help="Add action %s to the list of actions" % self.allActions
        )
        self.configParser.add_option(
         "--noAction", action="temp_append_split",
         dest="noActions", metavar="ACTIONS",
         help="Don't perform action"
        )
        for action in self.allActions:
            Action = action[0].capitalize()+action[1:]
            self.configParser.add_option(
             "--only%s" % Action, action="temp_append_const",
             dest="onlyActions", const=action,
             help="Add %s to the limited list of actions" % action
            )
            self.configParser.add_option(
             "--no%s" % Action, action="temp_append_const",
             dest="noActions", const=action,
             help="Remove %s from the list of actions to perform" % action
            )

        # Child-specified options
        # TODO error checking for overlapping options
        if configOptions:
            for option in configOptions:
                self.configParser.add_option(*option[0], **option[1])

        # Initial-config-specified options
        configOptions = self.queryVar('configOptions')
        if configOptions:
            for option in configOptions:
                self.configParser.add_option(*option[0], **option[1])

    def parseConfigFile(self, fileName):
        """Read a config file and return a dictionary.
        """
        filePath = None
        searchPath = ['.', os.path.join(sys.path[0], 'configs')]
        for path in searchPath:
            if os.path.exists(os.path.join(path, fileName)):
                filePath = os.path.join(path, fileName)
                break
        else:
            self.error("Can't find %s in %s!" % (fileName, searchPath))
            return
        fh = open(filePath)
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

        # TODO Return it here? Or set something?
        return config

    def lockConfig(self):
        self.info("Locking configuration.")
        self.configLock = True

    def queryConfig(self, varName=None):
        return self._config

    def setConfig(self, config, overwrite=False):
        """It would be good to detect if self._config is already set, and
        if so, have settings as to how to determine what overrides what.
        """
        if self.configLock:
            self.error("Can't alter locked config!")
            return
        if self._config and not overwrite:
            for key, value in config.iteritems():
                self._config[key] = value
        else:
            self._config = config
        return self._config

    def queryVar(self, varName, default=None):
        if varName not in self._config or not self._config[varName]:
            return default
        else:
            return self._config[varName]

    def setVar(self, varName, value):
        if self.configLock:
            self.error("Can't alter locked config!")
            return
        self.debug("Setting %s to %s" % (varName, value))
        self._config[varName] = value
        return self.queryVar(varName)

    def setActions(self, actions):
        self.actions = actions
        return self.actions

    def queryAction(self, action):
        if action in self.actions:
            return True
        return False

    def queryActions(self):
        return self.actions

    def dumpConfig(self, config=None, fileName=None):
        """Dump the configuration somewhere, default to STDOUT.
        Be nice to be able to write a .py or .json file according to
        filename.

        TODO: write to file, verify that dump/load is exactly the same
        config.
        """
        if not config:
            config = self.queryConfig()
        if not fileName:
            pp = pprint.PrettyPrinter(indent=2, width=10)
            return pp.pformat(config)

    def loadConfig(self, configFile):
        """TODO: Write Me, Test Me
        Probably self._config = self.parseConfig(configFile)
        or something, but with more error checking.
        """
        if self.configLock:
            self.error("Can't alter locked config!")
            return
        pass

    def verifyActions(self, actionList):
        actions = ','.join(actionList).split(',')
        for action in actions:
            if action not in self.allActions:
                self.fatal("Invalid action %s not in %s!" % (action,
                                                             self.allActions))
        return actions

    def parseArgs(self):
        """Parse command line arguments in a generic way.
        Return the parser object after adding the basic options, so
        child objects can manipulate it.
        """
        self.commandLine = ' '.join(sys.argv)
        (options, args) = self.configParser.parse_args()

        if options.configFile:
            self.setConfig(self.parseConfigFile(options.configFile))
        elif self.requireConfigFile:
            self.fatal("You must specify --configFile!")
        for key in self.configParser.variables:
            value = getattr(options, key)
            if value and key in self.configParser.appendVariables:
                value = ','.join(value).split(',')
            if value is not None:
                self.setVar(key, value)

        """Actions.

        Seems a little complex, but the logic goes:

        If we specify --onlyBLAH once or multiple times, we want to override
        the defaultActions list with the ones we list.

        Otherwise, if we specify --addAction, we want to add an action to
        the default list.

        Finally, if we specify --noBLAH, remove that from the list of
        actions to perform.
        """
        actionsToRun = self.defaultActions
        if options.onlyActions:
            actions = self.verifyActions(options.onlyActions)
            actionsToRun = actions
        elif options.addActions:
            actions = self.verifyActions(options.addActions)
            actionsToRun.extend(actions)
        if options.noActions:
            actions = self.verifyActions(options.noActions)
            for action in actions:
                if action in actionsToRun:
                    actionsToRun.remove(action)
        self.setActions(actionsToRun)

        return (options, args)

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
class SimpleConfig(BaseConfig, BasicFunctions):
    """Effectively BaseConfig with logging.
    """
    def __init__(self, configOptions=[], logLevel="info", **kwargs):
        configOptions.append([
         ["--multiLog",],
         {"action": "store_true",
          "dest": "multiLog",
          "default": False,
          "help": "Log using MultiFileLogger"
         }
        ])
        BaseConfig.__init__(self, configOptions=configOptions, **kwargs)
        BasicFunctions.__init__(self)
        self.logLevel = logLevel
        self.newLogObj()
        self.info("Run as %s" % self.commandLine)

    def newLogObj(self):
        logConfig = {"loggerName": 'Simple',
                     "logName": 'test',
                     "logDir": 'logs',
                     "logLevel": self.logLevel,
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
    obj = SimpleConfig(initialConfigFile=os.path.join('test', 'test.json'),
                       logLevel="debug")
    obj.setVar('additionalkey', 'additionalvalue')
    obj.setVar('key2', 'value2override')
    obj.dumpConfig()
    obj.lockConfig()
    if obj.queryVar('key1') != "value1":
        obj.fatal("key1 isn't value1!")
    obj.info("You should see an error here about a locked config:")
    if obj.setVar("foo", "bar"):
        obj.fatal("Something's broken in lockConfig()!")
    obj.info("Things look good.")
    obj.rmtree("test_logs")
