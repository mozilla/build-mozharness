#!/usr/bin/env python
"""Generic config parsing and dumping, the way I remember it from scripts
gone by.

Ideally the config is loaded + mixed with command line options, then locked
during runtime.  The config dump should be loadable and re-runnable for a
duplicate run.

TODO:

* dumpConfig and loadConfig need to be seamless. And written.
* options with defaults are overwriting the defaults in the config
  files, which is good for some of 'em and bad for others.
* queryExe() ?
"""

from copy import deepcopy
from optparse import OptionParser, Option
import os
import pprint
import sys
try:
    import json
except:
    import simplejson as json
from log import SimpleFileLogger, MultiFileLogger, BasicFunctions



# optparse {{{1
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
        kwargs['option_class'] = ExtendOption
        OptionParser.__init__(self, **kwargs)
        self.variables = []
        self.append_variables = []

    def add_option(self, *args, **kwargs):
        temp_variable = False
        if 'temp' in kwargs:
            temp_variable = kwargs['temp']
            del(kwargs['temp'])
        option = OptionParser.add_option(self, *args, **kwargs)
        if option.dest and option.dest not in self.variables:
            if not temp_variable:
                self.variables.append(option.dest)

class ExtendOption(Option):
    """from http://docs.python.org/library/optparse.html?highlight=optparse#adding-new-actions"""
    ACTIONS = Option.ACTIONS + ("extend",)
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extend",)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extend",)
    ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + ("extend",)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "extend":
            lvalue = value.split(",")
            values.ensure_value(dest, []).extend(lvalue)
        else:
            Option.take_action(
                self, action, dest, opt, value, values, parser)



# BaseConfig {{{1
class BaseConfig(object):
    """Basic config setting/getting.
    Debating whether to be paranoid about this stuff and put it all in
    self._config+rand(10000) and forcing everyone to use methods to access
    it, as I did elsewhere to lock down the config during runtime, but
    that's a little heavy handed to go with as the default.
    """
    def __init__(self, config=None, initial_config_file=None, config_options=[],
                 all_actions=["clobber", "build"], default_actions=None,
                 require_config_file=False, usage="usage: %prog [options]"):
        self._config = {}
        self.actions = []
        self.log_obj = None
        self.config_lock = False
        self.require_config_file = require_config_file

        self.all_actions = all_actions
        if default_actions:
            self.default_actions = default_actions
        else:
            self.default_actions = all_actions

        if config:
            self.setConfig(config)
        if initial_config_file:
            self.setConfig(self.parseConfigFile(initial_config_file))
        self._createConfigParser(config_options, usage)
        self.parseArgs()

    def _createConfigParser(self, config_options, usage):
        self.config_parser = MozOptionParser(usage=usage)
        self.config_parser.add_option(
         "--log-level", action="store",
         type="choice", dest="log_level", default="info",
         choices=['debug', 'info', 'warning', 'error', 'critical', 'fatal'],
         help="Set log level (debug|info|warning|error|critical|fatal)"
        )
        self.config_parser.add_option(
         "-q", "--quiet", action="store_false", dest="log_to_console",
         default=True, help="Don't log to the console"
        )
        self.config_parser.add_option(
         "--append-to-log", action="store_true",
         dest="append_to_log", default=False,
         help="Append to the log"
        )
        self.config_parser.add_option(
         "--work-dir", action="store", dest="work_dir",
         type="string", default="work_dir",
         help="Specify the work_dir (subdir of base_work_dir)"
        )
        self.config_parser.add_option(
         "--base-work-dir", action="store", dest="base_work_dir",
         type="string", default=os.getcwd(),
         help="Specify the absolute path of the parent of the working directory"
        )
        self.config_parser.add_option(
         "--config-file", action="store", dest="config_file",
         type="string", help="Specify the config file (required)"
        )

        # Actions
        self.config_parser.add_option(
         "--action", action="extend", temp=True,
         dest="only_actions", metavar="ACTIONS",
         help="Do action %s" % self.all_actions
        )
        self.config_parser.add_option(
         "--add-action", action="extend", temp=True,
         dest="add_actions", metavar="ACTIONS",
         help="Add action %s to the list of actions" % self.all_actions
        )
        self.config_parser.add_option(
         "--no-action", action="extend", temp=True,
         dest="no_actions", metavar="ACTIONS",
         help="Don't perform action"
        )
        for action in self.all_actions:
            self.config_parser.add_option(
             "--only-%s" % action, action="append_const", temp=True,
             dest="only_actions", const=action,
             help="Add %s to the limited list of actions" % action
            )
            self.config_parser.add_option(
             "--no-%s" % action, action="append_const", temp=True,
             dest="no_actions", const=action,
             help="Remove %s from the list of actions to perform" % action
            )

        # Child-specified options
        # TODO error checking for overlapping options
        if config_options:
            for option in config_options:
                self.config_parser.add_option(*option[0], **option[1])

        # Initial-config-specified options
        config_options = self.queryVar('config_options')
        if config_options:
            for option in config_options:
                self.config_parser.add_option(*option[0], **option[1])

    def parseConfigFile(self, file_name):
        """Read a config file and return a dictionary.
        """
        file_path = None
        search_path = ['.', os.path.join(sys.path[0], '..', 'configs'),
                       os.path.join(sys.path[0], '..', '..', 'configs')]
        for path in search_path:
            if os.path.exists(os.path.join(path, file_name)):
                file_path = os.path.join(path, file_name)
                break
        else:
            self.error("Can't find %s in %s!" % (file_name, search_path))
            return
        fh = open(file_path)
        config = {}
        if file_name.endswith('.json'):
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
        self.config_lock = True

    def queryConfig(self, var_name=None):
        return self._config

    def setConfig(self, config, overwrite=False):
        """It would be good to detect if self._config is already set, and
        if so, have settings as to how to determine what overrides what.
        """
        if self.config_lock:
            self.error("Can't alter locked config!")
            return
        if self._config and not overwrite:
            for key, value in config.iteritems():
                self._config[key] = value
        else:
            self._config = config
        return self._config

    def existsVar(self, var_name):
        if var_name in self._config:
            return True

    def queryVar(self, var_name, default=None):
        # TODO return self.queryVARNAME if var_name in self.specialVars ?
        # if so, remember to update existsVar()
        if var_name not in self._config or not self._config[var_name]:
            return default
        else:
            return self._config[var_name]

    def setVar(self, var_name, value):
        if self.config_lock:
            self.error("Can't alter locked config!")
            return
        self.debug("Setting %s to %s" % (var_name, value))
        self._config[var_name] = value
        return self.queryVar(var_name)

    def setActions(self, actions):
        self.actions = actions
        return self.actions

    def queryAction(self, action):
        if action in self.actions:
            return True
        return False

    def queryActions(self):
        return self.actions

    def dumpConfig(self, config=None, file_name=None):
        """Dump the configuration somewhere, default to STDOUT.
        Be nice to be able to write a .py or .json file according to
        filename.

        TODO: write to file, verify that dump/load is exactly the same
        config.
        """
        if not config:
            config = self.queryConfig()
        if not file_name:
            pp = pprint.PrettyPrinter(indent=2, width=10)
            return pp.pformat(config)

    def loadConfig(self, config_file):
        """TODO: Write Me, Test Me
        Probably self._config = self.parseConfig(config_file)
        or something, but with more error checking.
        """
        if self.config_lock:
            self.error("Can't alter locked config!")
            return
        pass

    def verifyActions(self, action_list):
        actions = ','.join(action_list).split(',')
        for action in actions:
            if action not in self.all_actions:
                self.fatal("Invalid action %s not in %s!" % (action,
                                                             self.all_actions))
        return actions

    def parseArgs(self):
        """Parse command line arguments in a generic way.
        Return the parser object after adding the basic options, so
        child objects can manipulate it.
        """
        self.command_line = ' '.join(sys.argv)
        (options, args) = self.config_parser.parse_args()
        defaults = self.config_parser.defaults.copy()

        if options.config_file:
            self.setConfig(self.parseConfigFile(options.config_file))
        elif self.require_config_file:
            self.fatal("You must specify --config-file!")
        for key in self.config_parser.variables:
            value = getattr(options, key)
            if value is None:
                continue
            # Don't override config_file defaults with config_parser defaults
            if key in defaults and value == defaults[key] and self.existsVar(key):
                continue
            self.setVar(key, value)

        """Actions.

        Seems a little complex, but the logic goes:

        If we specify --only-BLAH once or multiple times, we want to override
        the default_actions list with the ones we list.

        Otherwise, if we specify --add-action, we want to add an action to
        the default list.

        Finally, if we specify --no-BLAH, remove that from the list of
        actions to perform.
        """
        actions_to_run = self.default_actions
        if options.only_actions:
            actions = self.verifyActions(options.only_actions)
            actions_to_run = actions
        elif options.add_actions:
            actions = self.verifyActions(options.add_actions)
            actions_to_run.extend(actions)
        if options.no_actions:
            actions = self.verifyActions(options.no_actions)
            for action in actions:
                if action in actions_to_run:
                    actions_to_run.remove(action)
        self.setActions(actions_to_run)

        return (options, args)

    """There may be a better way of doing this, but I did this previously...
    """
    def log(self, message, level='info', exit_code=-1):
        if self.log_obj:
            return self.log_obj.log(message, level=level, exit_code=exit_code)
        if level == 'info':
            print message
        elif level == 'debug':
            print 'DEBUG: %s' % message
        elif level in ('warning', 'error', 'critical'):
            print >> sys.stderr, "%s: %s" % (level.upper(), message)
        elif level == 'fatal':
            print >> sys.stderr, "FATAL: %s" % message
            sys.exit(exit_code)

    def debug(self, message):
        level = self.queryVar('log_level')
        if not level:
            level = self.queryVar('log_level')
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

    def fatal(self, message, exit_code=-1):
        self.log(message, level='fatal', exit_code=exit_code)



# SimpleConfig {{{1
class SimpleConfig(BaseConfig, BasicFunctions):
    """Effectively BaseConfig with logging.
    """
    def __init__(self, config_options=[], log_level="info", **kwargs):
        config_options.append([
         ["--multi-log",],
         {"action": "store_true",
          "dest": "multi_log",
          "default": False,
          "help": "Log using MultiFileLogger"
         }
        ])
        BaseConfig.__init__(self, config_options=config_options, **kwargs)
        BasicFunctions.__init__(self)
        self.log_level = log_level
        self.newLogObj()
        self.info("Run as %s" % self.command_line)

    def newLogObj(self):
        log_config = {"logger_name": 'Simple',
                      "log_name": 'test',
                      "log_dir": 'logs',
                      "log_level": self.log_level,
                      "log_format": '%(asctime)s - %(levelname)s - %(message)s',
                      "log_to_console": True,
                      "append_to_log": False,
                     }
        for key in log_config.keys():
            value = self.queryVar(key)
            if value:
                log_config[key] = value
        if self.queryVar("multi_log"):
            self.log_obj = MultiFileLogger(**log_config)
        else:
            self.log_obj = SimpleFileLogger(**log_config)



# __main__ {{{1
if __name__ == '__main__':
    obj = SimpleConfig(initial_config_file=os.path.join('test', 'test.json'),
                       log_level="debug")
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
