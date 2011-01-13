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
        (options, args) = parser.parse_args()
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
        self._lock = False
        self.update(dictionary.copy())

    def _check_lock(self):
        assert not self._lock, "ReadOnlyDict is locked!"

    def lock(self):
        self._lock = True

    def __setitem__(self, *args):
        self._check_lock()
        return dict.__setitem__(self, *args)

    def __delitem__(self, *args):
        self._check_lock()
        return dict.__delitem__(self, *args)

    def clear(self, *args):
        self._check_lock()
        return dict.clear(self, *args)

    def pop(self, *args):
        self._check_lock()
        return dict.pop(self, *args)

    def popitem(self, *args):
        self._check_lock()
        return dict.popitem(self, *args)

    def setdefault(self, *args):
        self._check_lock()
        return dict.setdefault(self, *args)

    def update(self, *args):
        self._check_lock()
        dict.update(self, *args)



# parse_config_file {{{1
def parse_config_file(file_name, quiet=False, search_path=None):
    """Read a config file and return a dictionary.
    """
    # TODO error checking.  Does this need to be part of an object with
    # self.log() functions?
    file_path = None
    if not search_path:
        search_path = ['.', os.path.join(sys.path[0], '..', 'configs'),
                       os.path.join(sys.path[0], '..', '..', 'configs')]
    for path in search_path:
        if os.path.exists(os.path.join(path, file_name)):
            file_path = os.path.join(path, file_name)
            break
    else:
        if not quiet:
            print "ERROR: Can't find %s in %s!" % (file_name, search_path)
        return
    if file_name.endswith('.py'):
        global_dict = {}
        local_dict = {}
        execfile(file_path, global_dict, local_dict)
        config = local_dict['config']
    else:
        fh = open(file_path)
        config = {}
        if file_name.endswith('.json'):
            json_config = json.load(fh)
            config = dict(json_config)
        else:
            # TODO better default? I'd self.fatal if it were available here.
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
    """
    def __init__(self, config=None, initial_config_file=None, config_options=None,
                 all_actions=None, default_actions=None,
                 volatile_config_vars=None,
                 require_config_file=False, usage="usage: %prog [options]"):
        self._config = {}
        self.actions = []
        self.config_lock = False
        self.require_config_file = require_config_file

        if all_actions:
            self.all_actions = all_actions[:]
        else:
            self.all_actions = ['clobber', 'build']
        if default_actions:
            self.default_actions = default_actions[:]
        else:
            self.default_actions = self.all_actions
        if volatile_config_vars is None:
            self.volatile_config_vars = []
        else:
            self.volatile_config_vars = volatile_config_vars[:]

        if config:
            self.set_config(config)
        if initial_config_file:
            self.set_config(parse_config_file(initial_config_file))
        if config_options is None:
            config_options = []
        self._create_config_parser(config_options, usage)
        self.parse_args()

    def get_read_only_config(self):
        return ReadOnlyDict(self._config)

    def _create_config_parser(self, config_options, usage):
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
        self.config_parser.add_option(
         "--noop", "--dry-run", action="store_true", default=False,
         dest="noop",
         help="Echo commands without executing them."
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
                                          'no_actions', 'list_actions',
                                          'noop'])
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

    def set_config(self, config, overwrite=False):
        """This is probably doable some other way."""
        if self._config and not overwrite:
            for key, value in config.iteritems():
                self._config[key] = value
        else:
            self._config = config
        return self._config

    def get_actions(self):
        return self.actions

    def dump_config(self, config=None, file_name=None):
        """Dump the configuration somewhere, default to STDOUT.
        Be nice to be able to write a .py or .json file according to
        filename.

        TODO: write to file, verify that dump/load is exactly the same
        config.
        """
        if not config:
            config = {}
            for key in self._config.keys():
                if key not in self.volatile_config_vars:
                    config[key] = self._config[key]
        json_config = json.dumps(config, sort_keys=True, indent=4)
        if not file_name:
            return json_config
        else:
            fh = open(file_name, 'w')
            fh.write(json_config)
            fh.close()

    def verify_actions(self, action_list, quiet=False):
        for action in action_list:
            if action not in self.all_actions:
                if not quiet:
                    print("Invalid action %s not in %s!" % (action,
                                                            self.all_actions))
                sys.exit(-1)
        return action_list

    def parse_args(self, args=None):
        """Parse command line arguments in a generic way.
        Return the parser object after adding the basic options, so
        child objects can manipulate it.
        """
        self.command_line = ' '.join(sys.argv)
        if not args:
            args = sys.argv[:]
        (options, args) = self.config_parser.parse_args(args)
        if options.list_actions:
            print "Actions available: " + ', '.join(self.all_actions)
            if self.default_actions != self.all_actions:
                print "Default actions: " + ', '.join(self.default_actions)
            sys.exit(0)

        defaults = self.config_parser.defaults.copy()

        if not options.config_file:
            c = parse_config_file('localconfig.json', quiet=True)
            if c:
                self.set_config(c)
            elif self.require_config_file:
                print("Required config file not set!")
                sys.exit(-1)
        else:
            self.set_config(parse_config_file(options.config_file))
        for key in self.config_parser.variables:
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
            actions = self.verify_actions(options.only_actions)
            self.actions = actions
        elif options.add_actions:
            actions = self.verify_actions(options.add_actions)
            self.actions.extend(actions)
        if options.no_actions:
            actions = self.verify_actions(options.no_actions)
            for action in actions:
                if action in self.actions:
                    self.actions.remove(action)

        return (options, args)



# __main__ {{{1
if __name__ == '__main__':
    pass
