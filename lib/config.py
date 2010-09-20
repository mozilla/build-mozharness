#!/usr/bin/env python
"""Generic config parsing and dumping, the way I remember it from scripts
gone by.

The config should be built from script-level defaults, overlaid by
config-file defaults, overlaid by command line options.

  (For buildbot-analogues that would be factory-level defaults,
   builder-level defaults, and build request/scheduler settings.)

The config should then be locked (set to read-only, to prevent runtime
alterations).  Afterwards we should dump the config to a file that is
uploaded with the build, and can be used to debug or replicate the build
at a later time.

TODO:

* env?
* checkRequiredSettings or something -- run at init, assert that
  these settings are set.
"""

from copy import deepcopy
from optparse import OptionParser, Option
import os
import sys
try:
    import json
except:
    import simplejson as json



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

    def add_option(self, *args, **kwargs):
        option = OptionParser.add_option(self, *args, **kwargs)
        if option.dest and option.dest not in self.variables:
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



# ReadOnlyDict {{{1
class ReadOnlyDict(dict):
    def __init__(self, dictionary):
        self.__lock = False
        self.update(dictionary.copy())

    def __checkLock__(self):
        assert not self.__lock, "ReadOnlyDict is locked!"

    def lock(self):
        self.__lock = True

    def __setitem__(self, *args):
        self.__checkLock__()
        return dict.__setitem__(self, *args)

    def __delitem__(self, *args):
        self.__checkLock__()
        return dict.__delitem__(self, *args)

    def clear(self, *args):
        self.__checkLock__()
        return dict.clear(self, *args)

    def pop(self, *args):
        self.__checkLock__()
        return dict.pop(self, *args)

    def popitem(self, *args):
        self.__checkLock__()
        return dict.popitem(self, *args)

    def setdefault(self, *args):
        self.__checkLock__()
        return dict.setdefault(self, *args)

    def update(self, *args):
        self.__checkLock__()
        dict.update(self, *args)



# parseConfigFile {{{1
def parseConfigFile(file_name):
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
        print "ERROR: Can't find %s in %s!" % (file_name, search_path)
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

    return config



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
                 volatile_config_vars=None,
                 require_config_file=False, usage="usage: %prog [options]"):
        self._config = {}
        self.actions = []
        self.config_lock = False
        self.require_config_file = require_config_file

        self.all_actions = all_actions
        if default_actions:
            self.default_actions = default_actions
        else:
            self.default_actions = all_actions

        if volatile_config_vars is None:
            self.volatile_config_vars = []
        else:
            self.volatile_config_vars = volatile_config_vars

        if config:
            self.setConfig(config)
        if initial_config_file:
            self.setConfig(parseConfigFile(initial_config_file))
        self._createConfigParser(config_options, usage)
        self.parseArgs()

    def getReadOnlyConfig(self):
        return ReadOnlyDict(self._config)

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
         default="localconfig.json",
         type="string", help="Specify the config file (required)"
        )

        # Actions
        self.config_parser.add_option(
         "--list-actions", action="store_true",
         dest="list_actions",
         help="List all available actions, then exit"
        )
        self.config_parser.add_option(
         "--action", action="extend",
         dest="only_actions", metavar="ACTIONS",
         help="Do action %s" % self.all_actions
        )
        self.config_parser.add_option(
         "--add-action", action="extend",
         dest="add_actions", metavar="ACTIONS",
         help="Add action %s to the list of actions" % self.all_actions
        )
        self.config_parser.add_option(
         "--no-action", action="extend",
         dest="no_actions", metavar="ACTIONS",
         help="Don't perform action"
        )
        for action in self.all_actions:
            self.config_parser.add_option(
             "--only-%s" % action, action="append_const",
             dest="only_actions", const=action,
             help="Add %s to the limited list of actions" % action
            )
            self.config_parser.add_option(
             "--no-%s" % action, action="append_const",
             dest="no_actions", const=action,
             help="Remove %s from the list of actions to perform" % action
            )
        self.volatile_config_vars.extend(['only_actions', 'add_actions',
                                          'no_actions', 'list_actions'])
        # Child-specified options
        # TODO error checking for overlapping options
        if config_options:
            for option in config_options:
                self.config_parser.add_option(*option[0], **option[1])

        # Initial-config-specified options
        config_options = self._config.get('config_options', None)
        if config_options:
            for option in config_options:
                self.config_parser.add_option(*option[0], **option[1])

    def setConfig(self, config, overwrite=False):
        """This is probably doable some other way."""
        if self._config and not overwrite:
            for key, value in config.iteritems():
                self._config[key] = value
        else:
            self._config = config
        return self._config

    def getActions(self):
        return self.actions

    def dumpConfig(self, config=None, file_name=None):
        """Dump the configuration somewhere, default to STDOUT.
        Be nice to be able to write a .py or .json file according to
        filename.

        TODO: write to file, verify that dump/load is exactly the same
        config.
        """
        if not config:
            config = self._config
        json_config = json.dumps(config, sort_keys=True, indent=4)
        if not file_name:
            return json_config
        else:
            fh = open(file_name, 'w')
            fh.write(json_config)
            fh.close()

    def verifyActions(self, action_list):
        actions = ','.join(action_list).split(',')
        for action in actions:
            if action not in self.all_actions:
                print("Invalid action %s not in %s!" % (action,
                                                        self.all_actions))
                sys.exit(-1)
        return actions

    def parseArgs(self):
        """Parse command line arguments in a generic way.
        Return the parser object after adding the basic options, so
        child objects can manipulate it.
        """
        self.command_line = ' '.join(sys.argv)
        (options, args) = self.config_parser.parse_args()
        if options.list_actions:
            print "Actions available: " + ', '.join(self.all_actions)
            sys.exit(0)

        defaults = self.config_parser.defaults.copy()

        self.setConfig(parseConfigFile(options.config_file))
        for key in self.config_parser.variables:
            if key in self.volatile_config_vars:
                continue
            value = getattr(options, key)
            if value is None:
                continue
            # Don't override config_file defaults with config_parser defaults
            if key in defaults and value == defaults[key] and key in self._config:
                continue
            self._config[key] = value

        """Actions.

        Seems a little complex, but the logic goes:

        If we specify --only-BLAH once or multiple times, we want to override
        the default_actions list with the ones we list.

        Otherwise, if we specify --add-action, we want to add an action to
        the default list.

        Finally, if we specify --no-BLAH, remove that from the list of
        actions to perform.
        """
        self.actions = self.default_actions
        if options.only_actions:
            actions = self.verifyActions(options.only_actions)
            self.actions = actions
        elif options.add_actions:
            actions = self.verifyActions(options.add_actions)
            self.actions.extend(actions)
        if options.no_actions:
            actions = self.verifyActions(options.no_actions)
            for action in actions:
                if action in self.actions:
                    self.actions.remove(action)

        return (options, args)



# __main__ {{{1
if __name__ == '__main__':
    # ReadOnlyDict tests {{{2
    print "##### ReadOnlyDict tests"
    a = {
     'b':'2',
     'c':{'d': '4'},
     'e':['f', 'g'],
    }
    foo = ReadOnlyDict(a)
    if a == foo:
        print "PASS: was able to transfer a dict to ReadOnlyDict."
    else:
        print "FAIL: wasn't able to transfer a dict to ReadOnlyDict!"
    foo.popitem()
    if len(foo) == len(a) - 1:
        print "PASS: can popitem() when unlocked.."
    else:
        print "FAIL can't popitem() when unlocked!"
    foo = ReadOnlyDict(a)
    foo.pop('e')
    if len(foo) == len(a) - 1:
        print "PASS: can pop() when unlocked."
    else:
        print "FAIL can't pop() when unlocked."
    foo = ReadOnlyDict(a)
    foo['e'] = 'yarrr'
    if foo['e'] == 'yarrr':
        print "PASS: can set var when unlocked."
    else:
        print "FAIL: can't set var when unlocked."
    del foo['e']
    if len(foo) == len(a) - 1:
        print "PASS: can del when unlocked."
    else:
        print "FAIL: can't del when unlocked."
    foo.clear()
    if foo == {}:
        print "PASS: can clear() when unlocked."
    else:
        print "FAIL: can't clear() when unlocked!"
    for key in a.keys():
        foo.setdefault(key, a[key])
    if a == foo:
        print "PASS: can setdefault() when unlocked."
    else:
        print "FAIL: can't setdefault() when unlocked!"
    foo = ReadOnlyDict(a)
    foo.lock()
    try:
        foo['e'] = 2
    except:
        print "PASS: can't set a var when locked."
    else:
        print "FAIL: can set foo['e'] when locked."
    try:
        del foo['e']
    except:
        print "PASS: can't del a var when locked."
    else:
        print "FAIL: can del foo['e'] when locked."
    try:
        foo.popitem()
    except:
        print "PASS: can't popitem() when locked."
    else:
        print "FAIL: can popitem() when locked."
        print foo
    try:
        foo.update({})
    except:
        print "PASS: can't update() when locked."
    else:
        print "FAIL: can update() when locked."
        print foo
    try:
        foo.setdefault({'arr': 'yarr'})
    except:
        print "PASS: can't setdefault() when locked."
    else:
        print "FAIL: can setdefault() when locked."
        print foo
    try:
        foo.pop()
    except:
        print "PASS: can't pop() when locked."
    else:
        print "FAIL: can pop() when locked."
        print foo
    try:
        foo.clear()
    except:
        print "PASS: can't clear() when locked."
    else:
        print "FAIL: can clear() when locked."
        print foo
