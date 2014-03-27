#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
""" buildbase.py.

provides a base class for fx desktop builds
author: Jordan Lund

"""

import os
import pprint
import subprocess
import re
import time
import uuid
import copy
import glob
from itertools import chain

# import the power of mozharness ;)
import sys
from datetime import datetime
from mozharness.base.config import BaseConfig, parse_config_file
from mozharness.base.script import PostScriptRun
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.buildbot import BuildbotMixin, TBPL_SUCCESS, \
    TBPL_WORST_LEVEL_TUPLE, TBPL_STATUS_DICT, TBPL_EXCEPTION
from mozharness.mozilla.purge import PurgeMixin
from mozharness.mozilla.mock import MockMixin
from mozharness.mozilla.signing import SigningMixin
from mozharness.mozilla.mock import ERROR_MSGS as MOCK_ERROR_MSGS
from mozharness.base.log import OutputParser, ERROR
from mozharness.mozilla.buildbot import TBPL_RETRY, TBPL_FAILURE
from mozharness.mozilla.testing.unittest import tbox_print_summary
from mozharness.mozilla.testing.errors import TinderBoxPrintRe
from mozharness.base.log import FATAL

TBPL_UPLOAD_ERRORS = [
    {
        'regex': re.compile("Connection timed out"),
        'level': TBPL_RETRY,
    },
    {
        'regex': re.compile("Connection reset by peer"),
        'level': TBPL_RETRY,
    },
    {
        'regex': re.compile("Connection refused"),
        'level': TBPL_RETRY,
    }
]

SNIPPET_TEMPLATE = """version=2
type=%(type)s
url=%(url)s
hashFunction=sha512
hashValue=%(sha512_hash)s
size=%(size)d
build=%(buildid)s
displayVersion=%(version)s
appVersion=%(version)s
platformVersion=%(version)s
"""

MISSING_CFG_KEY_MSG = "The key '%s' could not be determined \
Please add this to your config."

ERROR_MSGS = {
    'undetermined_repo_path': 'The repo could not be determined. \
Please make sure that either "repo" is in your config or, if \
you are running this in buildbot, "repo_path" is in your buildbot_config.',
    'comments_undetermined': '"comments" could not be determined. This may be \
because it was a forced build.',
    'src_mozconfig_path_not_found': '"abs_src_mozconfig" path could not be \
determined. Please make sure it is a valid path off of "abs_src_dir"',
    'tooltool_manifest_undetermined': '"tooltool_manifest_src" not set, \
Skipping run_tooltool...',
}
ERROR_MSGS.update(MOCK_ERROR_MSGS)


### Output Parsers


class MakeUploadOutputParser(OutputParser):
    tbpl_error_list = TBPL_UPLOAD_ERRORS
    # let's create a switch case using name-spaces/dict
    # rather than a long if/else with duplicate code
    property_conditions = [
        # key: property name, value: condition
        ('symbolsUrl', "m.endswith('crashreporter-symbols.zip') or "
                       "m.endswith('crashreporter-symbols-full.zip')"),
        ('testsUrl', "m.endswith(('tests.tar.bz2', 'tests.zip'))"),
        ('unsignedApkUrl', "m.endswith('apk') and "
                           "'unsigned-unaligned' in m"),
        ('robocopApkUrl', "m.endswith('apk') and 'robocop' in m"),
        ('jsshellUrl', "'jsshell-' in m and m.endswith('.zip')"),
        ('completeMarUrl', "m.endswith('.complete.mar')"),
        ('partialMarUrl', "m.endswith('.mar') and '.partial.' in m"),
    ]

    def __init__(self, **kwargs):
        super(MakeUploadOutputParser, self).__init__(**kwargs)
        self.matches = {}
        self.tbpl_status = TBPL_SUCCESS

    def parse_single_line(self, line):
        prop_assigned = False
        pat = r'''^(https?://.*?\.(?:tar\.bz2|dmg|zip|apk|rpm|mar|tar\.gz))$'''
        m = re.compile(pat).match(line)
        if m:
            m = m.group(1)
            for prop, condition in self.property_conditions:
                if eval(condition):
                    self.matches[prop] = m
                    prop_assigned = True
                    break
            if not prop_assigned:
                # if we found a match but haven't identified the prop then this
                # is the packageURL. Let's consider this the else block
                self.matches['packageUrl'] = m

        # now let's check for retry errors which will give log levels:
        # tbpl status as RETRY and mozharness status as WARNING
        for error_check in self.tbpl_error_list:
            if error_check['regex'].search(line):
                self.num_warnings += 1
                self.warning(line)
                self.tbpl_status = self.worst_level(
                    error_check['level'], self.tbpl_status,
                    levels=TBPL_WORST_LEVEL_TUPLE
                )
                break
        else:
            self.info(line)


class CheckTestCompleteParser(OutputParser):
    tbpl_error_list = TBPL_UPLOAD_ERRORS

    def __init__(self, **kwargs):
        self.matches = {}
        super(CheckTestCompleteParser, self).__init__(**kwargs)
        self.pass_count = 0
        self.fail_count = 0
        self.leaked = False
        self.harness_err_re = TinderBoxPrintRe['harness_error']['full_regex']

    def parse_single_line(self, line):
        # Counts and flags.
        # Regular expression for crash and leak detections.
        if "TEST-PASS" in line:
            self.pass_count += 1
            return self.info(line)
        if "TEST-UNEXPECTED-" in line:
            # Set the error flags.
            # Or set the failure count.
            m = self.harness_err_re.match(line)
            if m:
                r = m.group(1)
                if r == "missing output line for total leaks!":
                    self.leaked = None
                else:
                    self.leaked = True
            else:
                self.fail_count += 1
            return self.warning(line)
        self.info(line)  # else

    def evaluate_parser(self):
        # Return the summary.
        summary = tbox_print_summary(self.pass_count,
                                     self.fail_count,
                                     self.leaked)
        self.info("TinderboxPrint: check<br/>%s\n" % summary)


class BuildingConfig(BaseConfig):
    # TODO add nosetests for this class
    def get_cfgs_from_files(self, all_config_files, parser):
        """ create a config based upon config files passed

        This is class specific. It recognizes certain config files
        by knowing how to combine them in an organized hierarchy
        """
        # override from BaseConfig

        # this is what we will return. It will represent each config
        # file name and its associated dict
        # eg ('builds/branch_specifics.py', {'foo': 'bar'})
        all_config_dicts = []
        # important config files
        variant_cfg_file = branch_cfg_file = pool_cfg_file = ''

        # we want to make the order in which the options were given
        # not matter. ie: you can supply --branch before --build-pool
        # or vice versa and the hierarchy will not be different

        #### The order from highest precedence to lowest is:
        ## There can only be one of these...
        # 1) build_pool: this can be either staging, pre-prod, and prod cfgs
        # 2) branch: eg: mozilla-central, cedar, cypress, etc
        # 3) build_variant: these could be known like asan and debug
        #                   or a custom config
        ##
        ## There can be many of these
        # 4) all other configs: these are any configs that are passed with
        #                       --cfg and --opt-cfg. There order is kept in
        #                       which they were passed on the cmd line. This
        #                       behaviour is maintains what happens by default
        #                       in mozharness
        ##
        ####

        # so, let's first assign the configs that hold a known position of
        # importance (1 through 3)
        for i, cf in enumerate(all_config_files):
            if parser.build_pool:
                if cf == BuildOptionParser.build_pools[parser.build_pool]:
                    pool_cfg_file = all_config_files[i]

            if cf == BuildOptionParser.branch_cfg_file:
                branch_cfg_file = all_config_files[i]

            if cf == parser.build_variant:
                variant_cfg_file = all_config_files[i]

        # now remove these from the list if there was any.
        # we couldn't pop() these in the above loop as mutating a list while
        # iterating through it causes spurious results :)
        for cf in [pool_cfg_file, branch_cfg_file, variant_cfg_file]:
            if cf:
                all_config_files.remove(cf)

        # now let's update config with the remaining config files.
        # this functionality is the same as the base class
        all_config_dicts.extend(
            super(BuildingConfig, self).get_cfgs_from_files(all_config_files,
                                                            parser)
        )

        # stack variant, branch, and pool cfg files on top of that,
        # if they are present, in that order
        if variant_cfg_file:
            # take the whole config
            all_config_dicts.append(
                (variant_cfg_file, parse_config_file(variant_cfg_file))
            )
        if branch_cfg_file:
            # take only the specific branch, if present
            branch_configs = parse_config_file(branch_cfg_file)
            if branch_configs.get(parser.branch or ""):
                all_config_dicts.append(
                    (branch_cfg_file, branch_configs[parser.branch])
                )
        if pool_cfg_file:
            # take only the specific pool. If we are here, the pool
            # must be present
            build_pool_configs = parse_config_file(pool_cfg_file)
            all_config_dicts.append(
                (pool_cfg_file, build_pool_configs[parser.build_pool])
            )
        return all_config_dicts


# noinspection PyUnusedLocal
class BuildOptionParser(object):
    # TODO add nosetests for this class
    platform = None
    bits = None
    config_file_search_path = [
        '.', os.path.join(sys.path[0], '..', 'configs'),
        os.path.join(sys.path[0], '..', '..', 'configs')
    ]

    # add to this list and you can automagically do things like
    # --custom-build-variant non-unified
    # and the script will pull up the appropriate path for the config
    # against the current platform and bits.
    # *It will warn and fail if there is not a config for the current
    # platform/bits
    build_variants = {
        'asan': 'builds/releng_sub_%s_configs/%s_asan.py',
        'debug': 'builds/releng_sub_%s_configs/%s_debug.py',
        'asan-and-debug': 'builds/releng_sub_%s_configs/%s_asan_and_debug.py',
        'stat-and-debug': 'builds/releng_sub_%s_configs/%s_stat_and_debug.py',
        'non-unified': 'builds/releng_sub_%s_configs/%s_non_unified.py',
        'debug-and-non-unified':
                'builds/releng_sub_%s_configs/%s_debug_and_non_unified.py',
    }
    build_pools = {
        'staging': 'builds/build_pool_specifics.py',
        'production': 'builds/build_pool_specifics.py',
    }
    branch_cfg_file = 'builds/branch_specifics.py'

    @classmethod
    def _query_pltfrm_and_bits(cls, target_option, options):
        """ determine platform and bits

        This can be from either from a supplied --platform and --bits
        or parsed from given config file names.
        """
        error_msg = (
            'Whoops!\nYou are trying to pass a shortname for '
            '%s. \nHowever, I need to know the %s to find the appropriate '
            'filename. You can tell me by passing:\n\t"%s" or a config '
            'filename via "--config" with %s in it. \nIn either case, these '
            'option arguments must come before --custom-build-variant.'
        )
        current_config_files = options.config_files or []
        if not cls.bits:
            # --bits has not been supplied
            # lets parse given config file names for 32 or 64
            for cfg_file_name in current_config_files:
                if '32' in cfg_file_name:
                    cls.bits = '32'
                    break
                if '64' in cfg_file_name:
                    cls.bits = '64'
                    break
            else:
                sys.exit(error_msg % (target_option, 'bits', '--bits',
                                      '"32" or "64"'))

        if not cls.platform:
            # --platform has not been supplied
            # lets parse given config file names for platform
            for cfg_file_name in current_config_files:
                if 'windows' in cfg_file_name:
                    cls.platform = 'windows'
                    break
                if 'mac' in cfg_file_name:
                    cls.platform = 'mac'
                    break
                if 'linux' in cfg_file_name:
                    cls.platform = 'linux'
                    break
            else:
                sys.exit(error_msg % (target_option, 'platform', '--platform',
                                      '"linux", "windows", or "mac"'))
        return cls.bits, cls.platform

    @classmethod
    def set_build_variant(cls, option, opt, value, parser):
        """ sets an extra config file.

        This is done by either taking an existing filepath or by taking a valid
        shortname coupled with known platform/bits.
        """

        valid_variant_cfg_path = None
        # first let's see if we were given a valid short-name
        if cls.build_variants.get(value):
            bits, pltfrm = cls._query_pltfrm_and_bits(opt, parser.values)
            prospective_cfg_path = cls.build_variants[value] % (pltfrm, bits)
        else:
            # this is either an incomplete path or an invalid key in
            # build_variants
            prospective_cfg_path = value

        if os.path.exists(prospective_cfg_path):
            # now let's see if we were given a valid pathname
            valid_variant_cfg_path = value
        else:
            # let's take our prospective_cfg_path and see if we can
            # determine an existing file
            for path in cls.config_file_search_path:
                if os.path.exists(os.path.join(path, prospective_cfg_path)):
                    # success! we found a config file
                    valid_variant_cfg_path = os.path.join(path,
                                                          prospective_cfg_path)
                    break

        if not valid_variant_cfg_path:
            # either the value was an indeterminable path or an invalid short
            # name
            sys.exit("Whoops!\n'--custom-build-variant' was passed but an "
                     "appropriate config file could not be determined. Tried "
                     "using: '%s' but it was either not:\n\t-- a valid "
                     "shortname: %s \n\t-- a valid path in %s \n\t-- a "
                     "valid variant for the given platform and bits." % (
                         prospective_cfg_path,
                         str(cls.build_variants.keys()),
                         str(cls.config_file_search_path)))
        parser.values.config_files.append(valid_variant_cfg_path)
        option.dest = valid_variant_cfg_path

    @classmethod
    def set_build_pool(cls, option, opt, value, parser):
        if cls.build_pools.get(value):
            # first let's add the build pool file where there may be pool
            # specific keys/values. Then let's store the pool name
            parser.values.config_files.append(cls.build_pools[value])
            setattr(parser.values, option.dest, value)  # the pool
        else:
            sys.exit(
                "Whoops!\n--build-pool was passed with '%s' but only "
                "'%s' are valid options" % (value, str(cls.build_pools.keys()))
            )

    @classmethod
    def set_build_branch(cls, option, opt, value, parser):
        # first let's add the branch_specific file where there may be branch
        # specific keys/values. Then let's store the branch name we are using
        parser.values.config_files.append(cls.branch_cfg_file)
        setattr(parser.values, option.dest, value)  # the branch name

    @classmethod
    def set_platform(cls, option, opt, value, parser):
        cls.platform = value
        setattr(parser.values, option.dest, value)

    @classmethod
    def set_bits(cls, option, opt, value, parser):
        cls.bits = value
        setattr(parser.values, option.dest, value)


# this global depends on BuildOptionParser and therefore can not go at the
# top of the file
BUILD_BASE_CONFIG_OPTIONS = [
    [['--developer-run', '--skip-buildbot-actions'], {
        "action": "store_false",
        "dest": "is_automation",
        "default": True,
        "help": "If this is running outside of Mozilla's build"
                "infrastructure, use this option. It ignores actions"
                "that are not needed and adds config checks."}],
    [['--platform'], {
        "action": "callback",
        "callback": BuildOptionParser.set_platform,
        "type": "string",
        "dest": "platform",
        "help": "Sets the platform we are running this against"
                " valid values: 'windows', 'mac', 'linux'"}],
    [['--bits'], {
        "action": "callback",
        "callback": BuildOptionParser.set_bits,
        "type": "string",
        "dest": "bits",
        "help": "Sets which bits we are building this against"
                " valid values: '32', '64'"}],
    [['--custom-build-variant-cfg'], {
        "action": "callback",
        "callback": BuildOptionParser.set_build_variant,
        "type": "string",
        "dest": "build_variant",
        "help": "Sets the build type and will determine appropriate"
                " additional config to use. Either pass a config path"
                " or use a valid shortname from: "
                "%s" % (BuildOptionParser.build_variants.keys(),)}],
    [['--build-pool'], {
        "action": "callback",
        "callback": BuildOptionParser.set_build_pool,
        "type": "string",
        "dest": "build_pool",
        "help": "This will update the config with specific pool"
                " environment keys/values. The dicts for this are"
                " in %s\nValid values: staging or"
                " production" % ('builds/build_pool_specifics.py',)}],
    [['--branch'], {
        "action": "callback",
        "callback": BuildOptionParser.set_build_branch,
        "type": "string",
        "dest": "branch",
        "help": "This sets the branch we will be building this for."
                " If this branch is in branch_specifics.py, update our"
                " config with specific keys/values from that. See"
                " %s for possibilites" % (
                    BuildOptionParser.branch_cfg_file,
                )}],
    [['--enable-pgo'], {
        "action": "store_true",
        "dest": "pgo_build",
        "default": False,
        "help": "Sets the build to run in PGO mode"}],

    [['--enable-nightly'], {
        "action": "store_true",
        "dest": "nightly_build",
        "default": False,
        "help": "Sets the build to run in nightly mode"}],
]


class BuildScript(BuildbotMixin, PurgeMixin, MockMixin,
                  SigningMixin, MercurialScript):
    def __init__(self, **kwargs):
        # objdir is referenced in _query_abs_dirs() so let's make sure we
        # have that attribute before calling BaseScript.__init__
        self.objdir = None
        super(BuildScript, self).__init__(**kwargs)
        # epoch is only here to represent the start of the buildbot build
        # that this mozharn script came from. until I can grab bbot's
        # status.build.gettime()[0] this will have to do as a rough estimate
        # although it is about 4s off from the time it would be if it was
        # done through MBF.
        # TODO find out if that time diff matters or if we just use it to
        # separate each build
        self.epoch_timestamp = int(time.mktime(datetime.now().timetuple()))
        self.branch = self.config.get('branch')
        self.bits = self.config.get('bits')
        self.platform = self.config.get('platform')
        if self.bits == '64' and not self.platform.endswith('64'):
            self.platform += '64'
        self.repo_path = None
        self.revision = None
        self.buildid = None
        self.builduid = None
        self.query_buildid()  # sets self.buildid
        self.query_builduid()  # sets self.builduid

    def _pre_config_lock(self, rw_config):
        c = self.config
        build_pool = c.get('build_pool', '')
        cfg_match_msg = "Script was ran with '%(option)s %(type)s' and \
%(type)s matches a key in '%(type_config_file)s'. Updating self.config with \
items from that key's value."
        pf_override_msg = "The branch '%(branch)s' has custom behavior for the \
platform '%(platform)s'. Updating self.config with the following from \
'platform_overrides' found in '%(pf_cfg_file)s':"
        cfg_files_and_dicts = rw_config.all_cfg_files_and_dicts
        for i, (target_file, target_dict) in enumerate(cfg_files_and_dicts):
            if BuildOptionParser.branch_cfg_file == target_file:
                self.info(
                    cfg_match_msg % {
                        'option': '--branch',
                        'type': c['branch'],
                        'type_config_file': BuildOptionParser.branch_cfg_file
                    }
                )
            if target_file == BuildOptionParser.build_pools.get(build_pool):
                self.info(
                    cfg_match_msg % {
                        'option': '--build-pool',
                        'type': c['build_pool'],
                        'type_config_file': BuildOptionParser.build_pools[
                            c['build_pool']
                        ]
                    }
                )
        if c.get("platform_overrides"):
            if c['platform'] in c['platform_overrides'].keys():
                self.info(
                    pf_override_msg % {
                        'branch': c['branch'],
                        'platform': c['platform'],
                        'pf_cfg_file': BuildOptionParser.branch_cfg_file
                    }
                )
                branch_pf_overrides = c['platform_overrides'][c['platform']]
                self.info(pprint.pformat(branch_pf_overrides))
                c.update(branch_pf_overrides)
        self.info('To generate a config file based upon options passed and '
                  'config files used, run script as before but extend options '
                  'with "--dump-config"')
        self.info('For a diff of where self.config got its items, '
                  'run the script again as before but extend options with: '
                  '"--dump-config-hierarchy"')
        self.info("Both --dump-config and --dump-config-hierarchy don't "
                  "actually run any actions.")

    def _assert_cfg_valid_for_action(self, dependencies, action):
        """ assert dependency keys are in config for given action.

        Takes a list of dependencies and ensures that each have an
        assoctiated key in the config. Displays error messages as
        appropriate.

        """
        # TODO add type and value checking, not just keys
        # TODO solution should adhere to: bug 699343
        # TODO add this to BaseScript when the above is done
        # for now, let's just use this as a way to save typing...
        c = self.config
        undetermined_keys = []
        err_template = "The key '%s' could not be determined \
and is needed for the action '%s'. Please add this to your config \
or run without that action (ie: --no-{action})"
        for dep in dependencies:
            if dep not in c:
                undetermined_keys.append(dep)
        if undetermined_keys:
            fatal_msgs = [err_template % (key, action)
                          for key in undetermined_keys]
            self.fatal("".join(fatal_msgs))
        # otherwise:
        return  # all good

    def _query_build_prop_from_app_ini(self, prop, app_ini_path=None):
        dirs = self.query_abs_dirs()
        print_conf_setting_path = os.path.join(dirs['abs_src_dir'],
                                               'config',
                                               'printconfigsetting.py')
        if not app_ini_path:
            # set the default
            app_ini_path = dirs['abs_app_ini_path']
        if (os.path.exists(print_conf_setting_path) and
                os.path.exists(app_ini_path)):
            cmd = [
                'python', print_conf_setting_path, app_ini_path,
                'App', prop
            ]
            return self.get_output_from_command(cmd, cwd=dirs['base_work_dir'])
        else:
            return ''

    def query_builduid(self):
        c = self.config
        if self.builduid:
            return self.builduid
        in_buildbot_props = False
        if c.get("is_automation"):
            if self.buildbot_config['properties'].get('builduid'):
                in_buildbot_props = True

        # let's see if it's in buildbot_properties
        if in_buildbot_props:
            self.info("Determining builduid from buildbot properties")
            self.builduid = self.buildbot_config['properties']['builduid']
        else:
            self.info("Creating builduid through uuid hex")
            self.builduid = uuid.uuid4().hex

        if self.builduid:
            if c.get('is_automation') and not in_buildbot_props:
                self.set_buildbot_property('builduid',
                                           self.buildid,
                                           write_to_file=True)
        else:
            # something went horribly wrong
            self.fatal("Could not determine builduid!")
        return self.builduid

    def query_buildid(self):
        c = self.config
        if self.buildid:
            return self.buildid
        in_buildbot_props = False
        if c.get("is_automation"):
            if self.buildbot_config['properties'].get('buildid'):
                in_buildbot_props = True

        # first let's see if we have already built ff
        # in which case we would have a buildid
        if self._query_build_prop_from_app_ini('BuildID'):
            self.info("Determining buildid from application.ini")
            self.buildid = self._query_build_prop_from_app_ini('BuildID')
        # now let's see if it's in buildbot_properties
        elif in_buildbot_props:
            self.info("Determining buildid from buildbot properties")
            self.buildid = self.buildbot_config['properties']['buildid']
        else:
            # finally, let's resort to making a buildid this will happen when
            #  buildbot has not made one, and we are running this script for
            # the first time in a clean clobbered state
            self.info("Creating buildid through current time")
            self.buildid = time.strftime("%Y%m%d%H%M%S",
                                         time.localtime(time.time()))
        if self.buildid:
            if c.get('is_automation') and not in_buildbot_props:
                self.set_buildbot_property('buildid',
                                           self.buildid,
                                           write_to_file=True)
        else:
            # something went horribly wrong
            self.fatal("Could not determine Buildid!")

        return self.buildid

    def _query_objdir(self):
        if self.objdir:
            return self.objdir

        if not self.config.get('objdir'):
            return self.fatal(MISSING_CFG_KEY_MSG % ('objdir',))
        self.objdir = self.config['objdir']
        return self.objdir

    def _query_repo(self):
        if self.repo_path:
            return self.repo_path
        c = self.config

        # unlike b2g, we actually supply the repo in mozharness so if it's in
        #  the config, we use that (automation does not require it in
        # buildbot props)
        if not c.get('repo_path'):
            repo_path = 'projects/%s' % (self.branch,)
            self.info(
                "repo_path not in config. Using '%s' instead" % (repo_path,)
            )
        else:
            repo_path = c['repo_path']
        self.repo_path = '%s/%s' % (c['repo_base'], repo_path,)
        return self.repo_path

    def _skip_buildbot_specific_action(self):
        """ ignore actions from buildbot's infra."""
        self.info("This action is specific to buildbot's infrastructure")
        self.info("Skipping......")
        return

    def query_build_env(self, skip_keys=None, replace_dict=None, **kwargs):
        c = self.config
        if skip_keys is None:
            skip_keys = []

        if not replace_dict:
            replace_dict = {}
        # now let's grab the right host based off staging/production
        # symbol_server_host is defined in build_pool_specifics.py
        replace_dict.update({"symbol_server_host": c['symbol_server_host']})

        # let's evoke the base query_env and make a copy of it
        # as we don't always want every key below added to the same dict
        env = copy.deepcopy(
            super(BuildScript, self).query_env(replace_dict=replace_dict,
                                               **kwargs)
        )

        if self.query_is_nightly():
            env["IS_NIGHTLY"] = "yes"
            if c["create_snippets"] and c['platform_supports_snippets']:
                # in branch_specifics.py we might set update_channel explicitly
                if c.get('update_channel'):
                    env["MOZ_UPDATE_CHANNEL"] = c['update_channel']
                else:  # let's just give the generic channel based on branch
                    env["MOZ_UPDATE_CHANNEL"] = "nightly-%s" % (self.branch,)

        if c.get('enable_signing') and 'MOZ_SIGN_CMD' not in skip_keys:
            moz_sign_cmd = self.query_moz_sign_cmd()
            env["MOZ_SIGN_CMD"] = subprocess.list2cmdline(moz_sign_cmd)
        else:
            # so SigningScriptFactory (what calls mozharness script
            # from buildbot) assigns  MOZ_SIGN_CMD but does so incorrectly
            # for desktop builds. Also, sometimes like for make l10n check,
            # we don't actually want it in the env
            if env.get("MOZ_SIGN_CMD"):
                del env["MOZ_SIGN_CMD"]

        # we can't make env an attribute of self because env can change on
        # every call for reasons like MOZ_SIGN_CMD
        return env

    def _ccache_z(self):
        """clear ccache stats."""
        self._assert_cfg_valid_for_action(['ccache_env'], 'build')
        c = self.config
        dirs = self.query_abs_dirs()
        env = self.query_build_env()
        # update env for just this command
        ccache_env = copy.deepcopy(c['ccache_env'])
        ccache_env['CCACHE_BASEDIR'] = c['ccache_env'].get(
            'CCACHE_BASEDIR', "") % {"base_dir": dirs['base_work_dir']}
        env.update(c['ccache_env'])
        if os.path.exists(dirs['abs_src_dir']):
            self.run_command(command=['ccache', '-z'],
                             cwd=dirs['abs_src_dir'],
                             env=env)

    def _rm_old_package(self):
        """rm the old package."""
        c = self.config
        dirs = self.query_abs_dirs()
        old_package_paths = []
        old_package_patterns = c.get('old_packages')

        self.info("removing old packages...")
        if os.path.exists(dirs['abs_obj_dir']):
            for product in old_package_patterns:
                old_package_paths.extend(
                    glob.glob(product % {"objdir": dirs['abs_obj_dir']})
                )
        if old_package_paths:
            for package_path in old_package_paths:
                self.rmtree(package_path)
        else:
            self.info("There wasn't any old packages to remove.")

    def _get_mozconfig(self):
        """assign mozconfig."""
        c = self.config
        dirs = self.query_abs_dirs()
        if c.get('src_mozconfig'):
            self.info('Using in-tree mozconfig')
            abs_src_mozconfig = os.path.join(dirs['abs_src_dir'],
                                             c.get('src_mozconfig'))
            if not os.path.exists(abs_src_mozconfig):
                self.info('abs_src_mozconfig: %s' % (abs_src_mozconfig,))
                self.fatal(ERROR_MSGS['src_mozconfig_path_not_found'])
            self.copyfile(abs_src_mozconfig,
                          os.path.join(dirs['abs_src_dir'], '.mozconfig'))
        else:
            self.fatal("To build, you must supply a mozconfig from inside the "
                       "tree to use use. Please provide the path in your "
                       "config via 'src_mozconfig'")

    # TODO add this or merge to ToolToolMixin
    def _run_tooltool(self):
        self._assert_cfg_valid_for_action(
            ['tooltool_script', 'tooltool_bootstrap', 'tooltool_url'],
            'build'
        )
        c = self.config
        dirs = self.query_abs_dirs()
        if not c.get('tooltool_manifest_src'):
            return self.warning(ERROR_MSGS['tooltool_manifest_undetermined'])
        fetch_script_path = os.path.join(dirs['abs_tools_dir'],
                                         'scripts/tooltool/fetch_and_unpack.sh')
        tooltool_manifest_path = os.path.join(dirs['abs_src_dir'],
                                              c['tooltool_manifest_src'])
        cmd = [
            fetch_script_path,
            tooltool_manifest_path,
            c['tooltool_url'],
            c['tooltool_script'],
            c['tooltool_bootstrap'],
        ]
        self.info(str(cmd))
        self.run_command(cmd, cwd=dirs['abs_src_dir'])

    def _checkout_source(self):
        """use vcs_checkout to grab source needed for build."""
        if self.revision:
            return self.revision
        c = self.config
        dirs = self.query_abs_dirs()
        repo = self._query_repo()
        rev = self.vcs_checkout(repo=repo, dest=dirs['abs_src_dir'])
        if c.get('is_automation'):
            changes = self.buildbot_config['sourcestamp']['changes']
            if changes:
                comments = changes[0].get('comments', '')
                self.set_buildbot_property('comments',
                                           comments,
                                           write_to_file=True)
            else:
                self.warning(ERROR_MSGS['comments_undetermined'])
            self.set_buildbot_property('got_revision',
                                       rev[:12],
                                       write_to_file=True)
        self.revision = rev[:12]
        return self.revision

    def _count_ctors(self):
        """count num of ctors and set testresults."""
        dirs = self.query_abs_dirs()
        abs_count_ctors_path = os.path.join(dirs['abs_tools_dir'],
                                            'buildfarm',
                                            'utils',
                                            'count_ctors.py')
        abs_libxul_path = os.path.join(dirs['abs_obj_dir'],
                                       'dist',
                                       'bin',
                                       'libxul.so')

        cmd = ['python', abs_count_ctors_path, abs_libxul_path]
        output = self.get_output_from_command(cmd, cwd=dirs['abs_src_dir'])
        output = output.split("\t")
        num_ctors = int(output[0])
        testresults = [('num_ctors', 'num_ctors', num_ctors, str(num_ctors))]
        self.set_buildbot_property('num_ctors',
                                   num_ctors,
                                   write_to_file=True)
        self.set_buildbot_property('testresults',
                                   testresults,
                                   write_to_file=True)

    def _create_complete_mar(self):
        # TODO use mar.py MIXINs
        self._assert_cfg_valid_for_action(
            ['mock_target', 'complete_mar_pattern'],
            'make-update'
        )
        self.info('Creating a complete mar:')
        c = self.config
        env = self.query_build_env()
        dirs = self.query_abs_dirs()
        dist_update_dir = os.path.join(dirs['abs_obj_dir'],
                                       'dist',
                                       'update')
        self.info('removing existing mar...')
        mar_file_results = glob.glob(os.path.join(dist_update_dir, '*.mar'))
        if mar_file_results:
            for mar_file in mar_file_results:
                self.rmtree(mar_file, error_level=FATAL)
        else:
            self.info('no existing mar found with pattern: %s' % (
                os.path.join(dist_update_dir, '*.mar'),))
        self.info('making a complete new mar...')
        update_pkging_path = os.path.join(dirs['abs_obj_dir'],
                                          'tools',
                                          'update-packaging')
        self.run_mock_command(c['mock_target'],
                              command='make -C %s' % (update_pkging_path,),
                              cwd=dirs['abs_src_dir'],
                              env=env)
        self._set_file_properties(file_name=c['complete_mar_pattern'],
                                  find_dir=dist_update_dir,
                                  prop_type='completeMar')

    def _create_partial_mar(self):
        # TODO use mar.py MIXINs and make this simpler
        self._assert_cfg_valid_for_action(
            ['mock_target', 'update_env', 'platform_ftp_name', 'stage_server'],
            'upload'
        )
        self.info('Creating a partial mar:')
        c = self.config
        dirs = self.query_abs_dirs()
        generic_env = self.query_build_env()
        update_env = dict(chain(generic_env.items(), c['update_env'].items()))
        abs_unwrap_update_path = os.path.join(dirs['abs_src_dir'],
                                              'tools',
                                              'update-packaging',
                                              'unwrap_full_update.pl')
        dist_update_dir = os.path.join(dirs['abs_obj_dir'],
                                       'dist',
                                       'update')
        self.info('removing old unpacked dirs...')
        for f in ['current', 'current.work', 'previous']:
            self.rmtree(os.path.join(dirs['abs_obj_dir'], f),
                        error_level=FATAL)
        self.info('making unpacked dirs...')
        for f in ['current', 'previous']:
            self.mkdir_p(os.path.join(dirs['abs_obj_dir'], f),
                         error_level=FATAL)
        self.info('unpacking current mar...')
        mar_file = self.query_buildbot_property('completeMarFilename')
        cmd = '%s %s %s' % (self.query_exe('perl'),
                            abs_unwrap_update_path,
                            os.path.join(dist_update_dir, mar_file))
        self.run_mock_command(c['mock_target'],
                              command=cmd,
                              cwd=os.path.join(dirs['abs_obj_dir'], 'current'),
                              env=update_env,
                              halt_on_failure=True)
        # The mar file name will be the same from one day to the next,
        # *except* when we do a version bump for a release. To cope with
        # this, we get the name of the previous complete mar directly
        # from staging. Version bumps can also often involve multiple mars
        # living in the latest dir, so we grab the latest one.
        self.info('getting previous mar filename...')
        latest_mar_dir = c['latest_mar_dir'] % {'branch': self.branch}
        cmd = 'ssh -l %s -i ~/.ssh/%s %s ls -1t %s | grep %s$ | head -n 1' % (
            c['stage_username'], c['stage_ssh_key'], c['stage_server'],
            latest_mar_dir, c['platform_ftp_name']
        )
        previous_mar_name = self.get_output_from_command(cmd)
        if re.search(r'\.mar$', previous_mar_name or ""):
            previous_mar_url = "http://%s%s/%s" % (c['stage_server'],
                                                   latest_mar_dir,
                                                   previous_mar_name)
            self.info('downloading previous mar...')
            previous_mar_file = self.download_file(previous_mar_url,
                                                   file_name='previous.mar',
                                                   parent_dir=dist_update_dir)
            if not previous_mar_file:
                # download_file will send error logs if this does not download
                return
        else:
            self.warning('could not determine the previous complete mar file')
            return
        self.info('unpacking previous mar...')
        cmd = '%s %s %s' % (self.query_exe('perl'),
                            abs_unwrap_update_path,
                            os.path.join(dist_update_dir, 'previous.mar'))
        self.run_mock_command(c['mock_target'],
                              command=cmd,
                              cwd=os.path.join(dirs['abs_obj_dir'],
                                               'previous'),
                              env=update_env)
        # Extract the build ID from the unpacked previous complete mar.
        previous_buildid = self._query_previous_buildid()
        self.info('removing pgc files from previous and current dirs')
        for mar_dir in ['current', 'previous']:
            target_path = os.path.join(dirs['abs_obj_dir'], mar_dir)
            if os.path.exists(target_path):
                for root, target_dirs, file_names in os.walk(target_path):
                    for file_name in file_names:
                        if file_name.endswith('.pgc'):
                            self.info('removing file: %s' % (file_name,))
                            os.remove(file_name)
        self.info("removing existing partial mar...")
        mar_file_results = glob.glob(
            os.path.join(dist_update_dir, '*.partial.*.mar')
        )
        if not mar_file_results:
            self.warning("Could not determine an existing partial mar from "
                         "%s pattern in %s dir" % ('*.partial.*.mar',
                                                   dist_update_dir))
        for mar_file in mar_file_results:
            self.rmtree(mar_file)

        self.info('generating partial patch from two complete mars...')
        update_env.update({
            'STAGE_DIR': '../../dist/update',
            'SRC_BUILD': '../../previous',
            'SRC_BUILD_ID': previous_buildid,
            'DST_BUILD': '../../current',
            'DST_BUILD_ID': self.query_buildid()
        })
        cmd = 'make -C tools/update-packaging partial-patch'
        self.run_mock_command(c.get('mock_target'),
                              command=cmd,
                              cwd=dirs['abs_obj_dir'],
                              env=update_env)
        self.rmtree(os.path.join(dist_update_dir, 'previous.mar'))
        self._set_file_properties(file_name=c['partial_mar_pattern'],
                                  find_dir=dist_update_dir,
                                  prop_type='partialMar')

    def _query_graph_server_branch_name(self):
        c = self.config
        if c.get('graph_server_branch_name'):
            return c['graph_server_branch_name']
        else:
            # capitalize every word in between '-'
            branch_list = self.branch.split('-')
            branch_list = [elem.capitalize() for elem in branch_list]
            return '-'.join(branch_list)

    def _graph_server_post(self):
        """graph server post results."""
        self._assert_cfg_valid_for_action(
            ['base_name', 'graph_server', 'graph_selector'],
            'generate-build-stats'
        )
        c = self.config
        dirs = self.query_abs_dirs()
        graph_server_post_path = os.path.join(dirs['abs_tools_dir'],
                                              'buildfarm',
                                              'utils',
                                              'graph_server_post.py')
        graph_server_path = os.path.join(dirs['abs_tools_dir'],
                                         'lib',
                                         'python')
        # graph server takes all our build properties we had initially
        # (buildbot_config) and what we updated to since
        # the script ran (buildbot_properties)
        # TODO it would be better to grab all the properties that were
        # persisted to file rather than use whats in the buildbot_properties
        # live object so we become less action dependant.
        graph_props_path = os.path.join(c['base_work_dir'],
                                        "graph_props.json")
        all_current_props = dict(
            chain(self.buildbot_config['properties'].items(),
                  self.buildbot_properties.items())
        )
        # graph_server_post.py expects a file with 'properties' key
        graph_props = dict(properties=all_current_props)
        self.dump_config(graph_props_path, graph_props)

        gs_env = self.query_build_env()
        gs_env.update({'PYTHONPATH': graph_server_path})
        resultsname = c['base_name'] % {'branch': self.branch}
        cmd = ['python', graph_server_post_path]
        cmd.extend(['--server', c['graph_server']])
        cmd.extend(['--selector', c['graph_selector']])
        cmd.extend(['--branch', self._query_graph_server_branch_name()])
        cmd.extend(['--buildid', self.query_buildid()])
        cmd.extend(['--sourcestamp',
                    self.query_buildbot_property('sourcestamp')])
        cmd.extend(['--resultsname', resultsname])
        cmd.extend(['--properties-file', graph_props_path])
        cmd.extend(['--timestamp', str(self.epoch_timestamp)])

        self.info("Obtaining graph server post results")
        result_code = self.retry(self.run_command,
                                 args=(cmd,),
                                 kwargs={'cwd': dirs['abs_src_dir'],
                                         'env': gs_env})
        if result_code != 0:
            self.add_summary('Automation Error: failed graph server post',
                             level=ERROR)
            self.worst_buildbot_status = self.worst_level(
                TBPL_EXCEPTION, self.worst_buildbot_status,
                TBPL_STATUS_DICT.keys()
            )

        else:
            self.info("graph server post ok")

    def _set_file_properties(self, file_name, find_dir, prop_type,
                             error_level=ERROR):
        c = self.config
        dirs = self.query_abs_dirs()
        error_msg = "Not setting props: %s{Filename, Size, Hash}" % prop_type
        cmd = ["find", find_dir, "-maxdepth", "1", "-type",
               "f", "-name", file_name]
        file_path = self.get_output_from_command(cmd,
                                                 dirs['abs_work_dir'])
        if not file_path:
            self.error(error_msg)
            self.error("Can't determine filepath with cmd: %s" % (str(cmd),))
            return

        cmd = [
            self.query_exe('openssl'), 'dgst',
            '-%s' % (c.get("hash_type", "sha512"),), file_path
        ]
        hash_prop = self.get_output_from_command(cmd, dirs['abs_work_dir'])
        if not hash_prop:
            self.log("undetermined hash_prop with cmd: %s" % (str(cmd),),
                     level=error_level)
            self.log(error_msg, level=error_level)
            return
        self.set_buildbot_property(prop_type + 'Filename',
                                   os.path.split(file_path)[1],
                                   write_to_file=True)
        self.set_buildbot_property(prop_type + 'Size',
                                   os.path.getsize(file_path),
                                   write_to_file=True)
        self.set_buildbot_property(prop_type + 'Hash',
                                   hash_prop.strip().split(' ', 2)[1],
                                   write_to_file=True)

    def _query_previous_buildid(self):
        dirs = self.query_abs_dirs()
        previous_buildid = self.query_buildbot_property('previous_buildid')
        if previous_buildid:
            return previous_buildid
        cmd = [
            "find", "previous", "-maxdepth", "4", "-type", "f", "-name",
            "application.ini"
        ]
        self.info("finding previous mar's inipath...")
        prev_ini_path = self.get_output_from_command(cmd,
                                                     cwd=dirs['abs_obj_dir'],
                                                     halt_on_failure=True)
        print_conf_path = os.path.join(dirs['abs_src_dir'],
                                       'config',
                                       'printconfigsetting.py')
        abs_prev_ini_path = os.path.join(dirs['abs_obj_dir'], prev_ini_path)
        previous_buildid = self.get_output_from_command(['python',
                                                         print_conf_path,
                                                         abs_prev_ini_path,
                                                         'App', 'BuildID'])
        if not previous_buildid:
            self.fatal("Could not determine previous_buildid. This property"
                       "requires the upload action creating a partial mar.")
        self.set_buildbot_property("previous_buildid",
                                   previous_buildid,
                                   write_to_file=True)
        return previous_buildid

    def _query_post_upload_cmd(self):
        # TODO support more from postUploadCmdPrefix()
        # as needed (as we introduce builds that use it)
        # h.m.o/build/buildbotcustom/process/factory.py#l119
        self._assert_cfg_valid_for_action(['stage_product'], 'upload')
        c = self.config
        post_upload_cmd = ["post_upload.py"]
        buildid = self.query_buildid()
        # if checkout src/dest exists, this should just return the rev
        revision = self._checkout_source()
        platform = self.platform
        if c.get('pgo_build'):
            platform += '-pgo'
        tinderbox_build_dir = "%s-%s" % (self.branch, platform)

        post_upload_cmd.extend(["--tinderbox-builds-dir", tinderbox_build_dir])
        post_upload_cmd.extend(["-p", c['stage_product']])
        post_upload_cmd.extend(['-i', buildid])
        post_upload_cmd.extend(['--revision', revision])
        post_upload_cmd.append('--release-to-tinderbox-dated-builds')
        if self.query_is_nightly():
            post_upload_cmd.extend(['-b', self.branch])
            post_upload_cmd.append('--release-to-dated')
            if c['platform_supports_post_upload_to_latest']:
                post_upload_cmd.append('--release-to-latest')
        return post_upload_cmd

    def _grab_mar_props(self, snippet_type='complete'):
        return (self.query_buildbot_property('%sMarUrl' % snippet_type),
                self.query_buildbot_property('%sMarHash' % snippet_type),
                self.query_buildbot_property('%sMarSize' % snippet_type))

    def _get_snippet_values(self, snippet_dir, snippet_type='complete',
                            error_level=ERROR):
        error_msg = ("Can't determine the '%s' prop and it's needed for "
                     "creating snippets. Please run the action 'upload' prior "
                     "to this")
        c = self.config
        buildid = self.query_buildid()
        url, hash_val, size = self._grab_mar_props(snippet_type)
        if not url or not hash_val or not size:
            mar_pattern = '%s_mar_pattern' % (snippet_type,)
            self.warning("Could not find the %s mar properties. Trying to find"
                         " them with %s pattern." % (snippet_type,
                                                     c[mar_pattern],))
            # note this will not find the mar url. If that is what is missing
            #  then we will have to run upload() along with this.
            self._assert_cfg_valid_for_action(
                [mar_pattern], 'update'
            )
            self._set_file_properties(
                file_name=c[mar_pattern],
                find_dir=snippet_dir, prop_type='%sMar' % snippet_type
            )
            # now try, try again!
            url, hash_val, size = self._grab_mar_props(snippet_type)
        version = self.query_buildbot_property('appVersion')
        if not version:
            self.warning("Could not find the appVersion property. Trying to "
                         "find it with it in application.ini")
            self.generate_build_props()
            # now try, try again!
            version = self.query_buildbot_property('appVersion')

        if not url:
            self.log(error_msg % ('%sMarUrl' % (snippet_type,),), error_level)
            return {}
        if not hash_val:
            self.log(error_msg % ('%sMarHash' % (snippet_type,),), error_level)
            return {}
        if not size:
            self.log(error_msg % ('%sMarSize' % (snippet_type,),), error_level)
            return {}
        if not version:
            self.log("Can't determine the '%s' prop. This is needed for "
                     "%sMar snippet generation." % ('appVersion', snippet_type),
                     error_level)
            return {}
        return {
            'type': snippet_type,
            'url': url,
            'sha512_hash': hash_val,
            'size': size,
            'buildid': buildid,
            'version': version,
        }

    def _create_snippet(self, snippet_type):
        # TODO port to mozharness/mozilla/signing.py.
        # right now, the existing create_snippet method is conducted
        # differently. these should be merged. however, snippet logic is on
        # it's way out. It's only used as a backup for balrog so it is not
        # high priority to port to signing.py
        self._assert_cfg_valid_for_action(
            ['mock_target'], 'update'
        )
        if snippet_type == 'complete':
            error_level = FATAL
        else:
            error_level = ERROR
        dirs = self.query_abs_dirs()
        snippet_dir = os.path.join(dirs['abs_obj_dir'],
                                   'dist',
                                   'update')
        if not os.path.exists(snippet_dir):
            self.fatal("The path: '%s' needs to exist for this action"
                       "Have you ran the 'build' action?" % (snippet_dir,))
        snippet_values = self._get_snippet_values(
            snippet_dir, snippet_type, error_level=error_level
        )
        if not snippet_values:
            self.error("A %s snippet could not be created." % snippet_type)
            return ''
        else:
            return SNIPPET_TEMPLATE % snippet_values

    def _submit_balrog_updates(self, balrog_type='nightly'):
        c = self.config
        dirs = self.query_abs_dirs()
        # first download buildprops_balrog.json this should be all the
        # buildbot properties we got initially (buildbot_config) and what
        # we have updated with since the script ran (buildbot_properties)
        # TODO it would be better to grab all the properties that were
        # persisted to file rather than use whats in the
        # buildbot_properties live object. However, this should work for
        # now and balrog may be removing the buildprops cli arg once we no
        # longer use buildbot
        balrog_props_path = os.path.join(c['base_work_dir'],
                                         "balrog_props.json")
        balrog_submitter_path = os.path.join(dirs['abs_tools_dir'],
                                             'scripts',
                                             'updates',
                                             'balrog-submitter.py')
        self.set_buildbot_property(
            'hashType', c.get('hash_type', 'sha512'), write_to_file=True
        )
        all_current_props = dict(
            chain(self.buildbot_config['properties'].items(),
                  self.buildbot_properties.items())
        )
        self.info("Dumping buildbot properties to %s." % balrog_props_path)
        balrog_props = dict(properties=all_current_props)
        self.dump_config(balrog_props_path, balrog_props)
        cmd = [
            self.query_exe('python'),
            balrog_submitter_path,
            '--build-properties', balrog_props_path,
            '--api-root', c['balrog_api_root'],
            '--username', c['balrog_username'],
            '-t', balrog_type, '--verbose',
        ]
        if c['balrog_credentials_file']:
            self.info("Using Balrog credential file...")
            abs_balrog_cred_file = os.path.join(
                c['base_work_dir'], c['balrog_credentials_file']
            )
            if not abs_balrog_cred_file:
                self.fatal("credential file given but doesn't exist!"
                           " Path given: %s" % abs_balrog_cred_file)
            cmd.extend(['--credentials-file', abs_balrog_cred_file])
        else:
            self.fatal("Balrog requires a credential file. Pease add the"
                       " path to your config via: 'balrog_credentials_file'")
        self.info("Submitting Balrog updates...")
        self.retry(
            self.run_command, args=(cmd,), kwargs={'halt_on_failure': True}
        )

    def preflight_build(self):
        """set up machine state for a complete build."""
        c = self.config
        if c.get('enable_ccache'):
            self._ccache_z()
        if not self.query_is_nightly():
            # the old package should live in source dir so we don't need to do
            # this for nighties since we clobber the whole work_dir in
            # clobber()
            self._rm_old_package()
        self._checkout_source()
        self._get_mozconfig()
        self._run_tooltool()

    def build(self):
        """build application."""
        # dependencies in config see _pre_config_lock
        base_cmd = 'make -f client.mk build'
        cmd = base_cmd + ' MOZ_BUILD_DATE=%s' % (self.query_buildid(),)
        if self.config.get('pgo_build'):
            cmd += ' MOZ_PGO=1'
        self.run_mock_command(self.config.get('mock_target'),
                              command=cmd,
                              cwd=self.query_abs_dirs()['abs_src_dir'],
                              env=self.query_build_env())

    def generate_build_props(self):
        """set buildid, sourcestamp, appVersion, and appName."""
        dirs = self.query_abs_dirs()
        print_conf_setting_path = os.path.join(dirs['abs_src_dir'],
                                               'config',
                                               'printconfigsetting.py')
        if (not os.path.exists(print_conf_setting_path) or
                not os.path.exists(dirs['abs_app_ini_path'])):
            self.error("Can't set the following properties: "
                       "buildid, sourcestamp, appVersion, and appName. "
                       "Required paths missing. Verify both %s and %s "
                       "exist. These paths require the 'build' action to be "
                       "run prior to this" % (print_conf_setting_path,
                                              dirs['abs_app_ini_path']))
        base_cmd = [
            'python', print_conf_setting_path, dirs['abs_app_ini_path'], 'App'
        ]
        properties_needed = [
            {'ini_name': 'SourceStamp', 'prop_name': 'sourcestamp'},
            {'ini_name': 'Version', 'prop_name': 'appVersion'},
            {'ini_name': 'Name', 'prop_name': 'appName'}
        ]
        for prop in properties_needed:
            prop_val = self.get_output_from_command(
                base_cmd + [prop['ini_name']], cwd=dirs['base_work_dir']
            )
            self.set_buildbot_property(prop['prop_name'],
                                       prop_val,
                                       write_to_file=True)

    def generate_build_stats(self):
        """grab build stats following a compile.

        This action handles all statitics from a build:
        count_ctors and graph_server_post.
        We only count_ctors for linux platforms and we only post to
        graph_server if this is not a nightly build
        """

        # NOTE: before this implementation, we would only tinderboxprint the
        # num_ctors to the log if this was a nightly build. I don't think
        # it's any harm doing so even if this is not nightly for the
        # benefit of making a simpler logic flow like below.
        c = self.config
        if not self.query_is_nightly() or c.get('enable_count_ctors'):
            if c.get('enable_count_ctors'):
                self._count_ctors()
                num_ctors = self.buildbot_properties.get('num_ctors', 'unknown')
                self.info("TinderboxPrint: num_ctors: %s" % (num_ctors,))
            if not self.query_is_nightly():
                self._graph_server_post()
            else:
                self.info("We are not posting to graph server as this is a "
                          "nightly build.")
        else:
            self.info("Nothing to do for this action since we disabled "
                      "count_ctors and we don't post to graph server for "
                      "nightlies")

    def symbols(self):
        c = self.config
        cwd = self.query_abs_dirs()['abs_obj_dir']
        env = self.query_build_env()
        self.run_mock_command(c.get('mock_target'),
                              command='make buildsymbols',
                              cwd=cwd,
                              env=env)
        # TODO this condition might be extended with xul, valgrind, etc as more
        # variants are added
        # not all nightly platforms upload symbols!
        if self.query_is_nightly() and c.get('upload_symbols'):
            # this is a bit confusing but every platform that make
            # uploadsymbols may or may not include a
            # MOZ_SYMBOLS_EXTRA_BUILDID in the env and the value of this
            # varies.
            # logic goes:
            #   If it's the release branch, we only include it for
            # 64bit platforms and we use just the platform as value.
            #   If it's a project branch off m-c, we include only the branch
            # for the value on 32 bit platforms and we include both the
            # platform and branch for 64 bit platforms
            moz_symbols_extra_buildid = ''
            if c.get('use_platform_in_symbols_extra_buildid'):
                moz_symbols_extra_buildid += self.platform
            if c.get('use_branch_in_symbols_extra_buildid'):
                if moz_symbols_extra_buildid:
                    moz_symbols_extra_buildid += '-%s' % (self.branch,)
                else:
                    moz_symbols_extra_buildid = self.branch
            if moz_symbols_extra_buildid:
                env['MOZ_SYMBOLS_EXTRA_BUILDID'] = moz_symbols_extra_buildid
            self.retry(
                self.run_mock_command,
                kwargs={'mock_target': c.get('mock_target'),
                        'command': 'make uploadsymbols',
                        'cwd': cwd,
                        'env': env}
            )

    def packages(self):
        self._assert_cfg_valid_for_action(['mock_target', 'package_filename'],
                                          'make-packages')
        c = self.config
        cwd = self.query_abs_dirs()['abs_obj_dir']

        # make package-tests
        if c.get('enable_package_tests'):
            self.run_mock_command(c['mock_target'],
                                  command='make package-tests',
                                  cwd=cwd,
                                  env=self.query_build_env())

        # make package
        self.run_mock_command(c['mock_target'],
                              command='make package',
                              cwd=cwd,
                              env=self.query_build_env())

    def upload(self):
        self._assert_cfg_valid_for_action(
            ['mock_target', 'upload_env', 'create_snippets',
             'platform_supports_snippets', 'create_partial',
             'platform_supports_partials', 'stage_server'], 'upload'
        )
        c = self.config
        if self.query_is_nightly():
            # if branch supports snippets and platform supports snippets
            if c['create_snippets'] and c['platform_supports_snippets']:
                self._create_complete_mar()
                if c['create_partial'] and c['platform_supports_partials']:
                    self._create_partial_mar()

        upload_env = self.query_build_env()
        upload_env.update(c['upload_env'])
        upload_env['UPLOAD_HOST'] = upload_env['UPLOAD_HOST'] % {
            "stage_server": c['stage_server']}

        # _query_post_upload_cmd returns a list (a cmd list), for env sake here
        # let's make it a string
        pst_up_cmd = ' '.join([str(i) for i in self._query_post_upload_cmd()])
        upload_env['POST_UPLOAD_CMD'] = pst_up_cmd
        parser = MakeUploadOutputParser(config=c,
                                        log_obj=self.log_obj)
        cwd = self.query_abs_dirs()['abs_obj_dir']
        self.retry(
            self.run_mock_command, kwargs={'mock_target': c.get('mock_target'),
                                           'command': 'make upload',
                                           'cwd': cwd,
                                           'env': upload_env,
                                           'output_parser': parser}
        )
        if parser.tbpl_status != TBPL_SUCCESS:
            self.add_summary("make upload failed")
        self.worst_buildbot_status = self.worst_level(
            parser.tbpl_status, self.worst_buildbot_status,
            TBPL_STATUS_DICT.keys()
        )
        self.info('Setting properties from make upload...')
        for prop, value in parser.matches.iteritems():
            self.set_buildbot_property(prop,
                                       value,
                                       write_to_file=True)

    def sendchanges(self):
        c = self.config

        installer_url = self.query_buildbot_property('packageUrl')
        tests_url = self.query_buildbot_property('testsUrl')
        sendchange_props = {
            'buildid': self.query_buildid(),
            'builduid': self.query_builduid(),
            'nightly_build': self.query_is_nightly(),
            'pgo_build': c.get('pgo_build', False),
        }
        # TODO insert check for uploadMulti factory 2526
        # if not self.uploadMulti when we introduce a platform/build that uses
        # uploadMulti

        if c.get('enable_talos_sendchange'):  # do talos sendchange
            if c.get('pgo_build'):
                build_type = 'pgo-'
            else:  # we don't do talos sendchange for debug so no need to check
                build_type = ''  # leave 'opt' out of branch for talos
            talos_branch = "%s-%s-%s%s" % (self.branch,
                                           self.platform,
                                           build_type,
                                           'talos')
            self.sendchange(downloadables=[installer_url],
                            branch=talos_branch,
                            username='sendchange',
                            sendchange_props=sendchange_props)
        if c.get('enable_package_tests'):  # do unittest sendchange
            # we need a way to make opt builds use pgo branch sendchanges.
            # if the branch supports is per_checkin and this platform is a
            # pgo platform: see branch_specifics.py, use pgo instead of opt.
            override_opt_branch = (self.platform in c['pgo_platforms'] and
                                   c.get('branch_uses_per_checkin_strategy'))
            if c.get('pgo_build') or override_opt_branch:
                build_type = 'pgo'
            elif c.get('debug_build'):
                build_type = 'debug'
            else:  # generic opt build
                build_type = 'opt'
            if c.get('unittest_platform'):
                platform = c['unittest_platform']
            else:
                platform = self.platform
            full_unittest_platform = "%s-%s" % (platform, build_type)
            unittest_branch = "%s-%s-%s" % (self.branch,
                                            full_unittest_platform,
                                            'unittest')
            self.sendchange(downloadables=[installer_url, tests_url],
                            branch=unittest_branch,
                            sendchange_props=sendchange_props)

    def pretty_names(self):
        self._assert_cfg_valid_for_action(
            ['mock_target'], 'pretty-names'
        )
        c = self.config
        dirs = self.query_abs_dirs()
        # we want the env without MOZ_SIGN_CMD
        env = self.query_build_env(skip_keys=['MOZ_SIGN_CMD'])
        base_cmd = 'make %s MOZ_PKG_PRETTYNAMES=1'

        # TODO  port below from process/factory.py line 1526 if we end up
        # porting mac before x-compiling
        # MAC OS X IMPLEMENTATION
        # if 'mac' in self.platform:
        #     self.addStep(ShellCommand(
        #                  name='postflight_all',
        #                  command=self.makeCmd + [
        #                  '-f', 'client.mk', 'postflight_all'],

        package_targets = ['package']
        # TODO  port below from process/factory.py line 1543
        # WINDOWS IMPLEMENTATION
        # if self.enableInstaller:
        #     pkg_targets.append('installer')
        for target in package_targets:
            self.run_mock_command(c['mock_target'],
                                  command=base_cmd % (target,),
                                  cwd=dirs['abs_obj_dir'],
                                  env=env)
        update_package_cmd = '-C %s' % (os.path.join(dirs['abs_obj_dir'],
                                                     'tools',
                                                     'update-packaging'),)
        self.run_mock_command(c['mock_target'],
                              command=base_cmd % (update_package_cmd,),
                              cwd=dirs['abs_src_dir'],
                              env=env)
        if c.get('do_pretty_name_l10n_check'):
            self.run_mock_command(c['mock_target'],
                                  command=base_cmd % ("l10n-check",),
                                  cwd=dirs['abs_obj_dir'],
                                  env=env)

    def check_l10n(self):
        self._assert_cfg_valid_for_action(
            ['mock_target'], 'check-l10n'
        )
        c = self.config
        dirs = self.query_abs_dirs()
        # we want the env without MOZ_SIGN_CMD
        env = self.query_build_env(skip_keys=['MOZ_SIGN_CMD'])
        self.run_mock_command(c['mock_target'],
                              command='make l10n-check',
                              cwd=dirs['abs_obj_dir'],
                              env=env)

    def check_test(self):
        self._assert_cfg_valid_for_action(
            ['mock_target', 'check_test_env', 'enable_checktests'],
            'check-test'
        )
        c = self.config
        if self.query_is_nightly() or not c['enable_checktests']:
            self.info("Skipping action because this is a nightly run...")
            return
        dirs = self.query_abs_dirs()
        abs_check_test_env = {}
        for env_var, env_value in c['check_test_env'].iteritems():
            abs_check_test_env[env_var] = os.path.join(dirs['abs_tools_dir'],
                                                       env_value)
        env = self.query_build_env()
        env.update(abs_check_test_env)
        parser = CheckTestCompleteParser(config=c,
                                         log_obj=self.log_obj)
        self.run_mock_command(c['mock_target'],
                              command='make -k check',
                              cwd=dirs['abs_obj_dir'],
                              env=env,
                              output_parser=parser)
        parser.evaluate_parser()

    def update(self):
        self._assert_cfg_valid_for_action(
            ['create_snippets', 'platform_supports_snippets',
             'create_partial', 'platform_supports_partials',
             'aus2_user', 'aus2_ssh_key', 'aus2_host',
             'aus2_base_upload_dir', 'update_platform', 'balrog_api_root',
             'balrog_username'],
            'update'
        )
        c = self.config
        dirs = self.query_abs_dirs()
        created_partial_snippet = False
        if (not self.query_is_nightly() or not c['create_snippets'] or
                not c['platform_supports_snippets']):
            self.info("Skipping action because this action is only done for "
                      "nightlies and that support/enable snippets...")
            return
        dist_update_dir = os.path.join(dirs['abs_obj_dir'],
                                       'dist',
                                       'update')
        base_ssh_cmd = 'ssh -l %s -i ~/.ssh/%s %s ' % (c['aus2_user'],
                                                       c['aus2_ssh_key'],
                                                       c['aus2_host'])
        root_aus_full_dir = "%s/%s/%s" % (c['aus2_base_upload_dir'],
                                          self.branch,
                                          c['update_platform'])
        ##### Create snippet steps
        # create a complete snippet
        abs_snippet_path = os.path.join(dist_update_dir,
                                        'complete.update.snippet')
        content = self._create_snippet('complete')
        if content:
            self.info('saving complete snippet to file...')
            if self.write_to_file(abs_snippet_path, content) is None:
                self.fatal("Unable to write %s snippet to %s!" % (
                    "complete", abs_snippet_path)
                )
        else:
            # we need to create a complete snippet. we shouldn't have made it
            #  here
            self.fatal("Creating complete snippet failed! Missing data for "
                       "template.")
        buildid = self.query_buildid()
        # if branch supports partials and platform supports partials
        if c['create_partial'] and c['platform_supports_partials']:
            # now create a partial snippet
            abs_snippet_path = os.path.join(dist_update_dir,
                                            'partial.update.snippet')
            content = self._create_snippet('partial')
            if content:
                self.info('saving partial snippet to file...')
                created_partial_snippet = True
                if self.write_to_file(abs_snippet_path, content) is None:
                    self.error("Unable to write %s snippet to %s!" % (
                        "partial", abs_snippet_path)
                    )
                    created_partial_snippet = False
                # let's change the buildid to be the previous buildid
                # because the previous upload dir uses that id
                buildid = self._query_previous_buildid()
            else:
                self.warning("Partial snippet failed to be created so the"
                             "AUS prev upload dir will use current buildid.")
        #####

        ##### Upload snippet steps
        self.info("Creating AUS previous upload dir")
        aus_prev_upload_dir = "%s/%s/en-US" % (root_aus_full_dir,
                                               buildid)
        cmd = 'mkdir -p %s' % (aus_prev_upload_dir,)
        self.retry(self.run_command, args=(base_ssh_cmd + cmd,))

        # make an upload command that supports complete and partial formatting
        upload_cmd = (
            'scp -o User=%s -o IdentityFile=~/.ssh/%s %s/%%s.update.snippet '
            '%s:%s/%%s.txt' % (c['aus2_user'], c['aus2_ssh_key'],
                               dist_update_dir, c['aus2_host'],
                               aus_prev_upload_dir)
        )
        self.info("uploading complete snippet")
        self.retry(self.run_command,
                   args=(upload_cmd % ('complete', 'complete'),))
        # if branch supports partials and platform supports partials
        if c['create_partial'] and c['platform_supports_partials']:
            if created_partial_snippet:
                self.info("Uploading partial snippet")
                self.retry(self.run_command,
                           args=(upload_cmd % ('partial', 'partial'),))
                self.info("creating aus current upload dir")
                aus_current_upload_dir = "%s/%s/en-US" % (root_aus_full_dir,
                                                          self.query_buildid())
                cmd = 'mkdir -p %s' % (aus_current_upload_dir,)
                self.retry(self.run_command, args=(base_ssh_cmd + cmd,))

                # Create remote empty complete/partial snippets for current
                # build.  Also touch the remote platform dir to defeat NFS
                # caching on the AUS webheads.
                self.info("creating empty snippets")
                cmd = 'touch %s/complete.txt %s/partial.txt %s' % (
                    aus_current_upload_dir, aus_current_upload_dir,
                    root_aus_full_dir
                )
                self.retry(self.run_command, args=(base_ssh_cmd + cmd,))
            else:
                self.error("Partial snippet failed to be created. Nothing to "
                           "be uploaded.")
        #####

        ##### submit balrog update steps
        if c['balrog_api_root']:
            self._submit_balrog_updates()
            #####

    def enable_ccache(self):
        dirs = self.query_abs_dirs()
        env = self.query_build_env()
        cmd = ['ccache', '-s']
        self.run_command(cmd, cwd=dirs['abs_src_dir'], env=env)

    def _post_fatal(self, message=None, exit_code=None):
        # until this script has more defined return_codes, let's make sure
        # that we at least set the return_code to a failure for things like
        # _summarize()
        self.return_code = 2

    @PostScriptRun
    def _summarize(self):
        if self.return_code != 0:
            # TODO this will need some work. Once we define various return
            # codes and correlate tbpl levels against it, we can have more
            # definitions for tbpl status
            # bug 985068 should lay the plumbing down for this work
            self.worst_buildbot_status = self.worst_level(
                TBPL_FAILURE, self.worst_buildbot_status, TBPL_STATUS_DICT
            )
        self.buildbot_status(self.worst_buildbot_status)
        self.summary()
