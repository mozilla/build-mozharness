#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""desktop_l10n.py

Firefox repacks
"""

import os
import sys
import tempfile
import ConfigParser
import copy

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.log import LogMixin
from mozharness.base.script import ScriptMixin


CONFIG = {
    "buildid_section": 'App',
    "buildid_option": "BuildID",
    "unpack_script": "unwrap_full_update.pl",
    "incremental_update_script": "make_incremental_update.sh",
    "update_packaging_dir": "tools/update-packaging",
}


def tools_environment(base_dir, binaries, env):
    """returns the env setting required to run mar and/or mbsdiff"""
    # bad code here - FIXIT
    for binary in binaries:
        binary_name = binary.replace(".exe", "").upper()
        env[binary_name] = os.path.join(base_dir, binary)
        # windows -> python -> perl -> sh
        # windows fix...
        env[binary_name] = env[binary_name].replace("\\", "/")
    return env


def query_ini_file(ini_file, section, option):
    ini = ConfigParser.SafeConfigParser()
    ini.read(ini_file)
    return ini.get(section, option)


def buildid_form_ini(ini_file):
    """reads an ini_file and returns the buildid"""
    return query_ini_file(ini_file,
                          CONFIG.get('buildid_section'),
                          CONFIG.get('buildid_option'))


# MarTool {{{1
class MarTool(ScriptMixin, LogMixin, object):
    """manages the mar tools executables"""
    def __init__(self, url, dst_dir, log_obj, binaries):
        self.url = url
        self.dst_dir = dst_dir
        self.binaries = binaries
        self.log_obj = log_obj
        self.config = CONFIG
        super(MarTool, self).__init__()

    def download(self):
        """downloads mar tools executables (mar,mbsdiff)
           and stores them local_dir()"""
        self.info("getting mar tools")
        self.mkdir_p(self.dst_dir)
        for binary in self.binaries:
            from_url = "/".join((self.url, binary))
            full_path = os.path.join(self.dst_dir, binary)
            if not os.path.exists(full_path):
                self.download_file(from_url, file_name=full_path)
                self.info("downloaded %s" % full_path)
            else:
                self.info("found %s, skipping download" % full_path)
            self.chmod(full_path, 0755)


# MarFile {{{1
class MarFile(ScriptMixin, LogMixin, object):
    """manages the downlad/unpack and incremental updates of mar files"""
    def __init__(self, mar_scripts, log_obj, filename=None, prettynames=0):
        self.filename = filename
        super(MarFile, self).__init__()
        self.log_obj = log_obj
        self.build_id = None
        self.mar_scripts = mar_scripts
        self.prettynames = str(prettynames)
        self.config = CONFIG

    def unpack_mar(self, dst_dir):
        """unpacks a mar file into dst_dir"""
        self.download()
        # downloading mar tools
        cmd = ['perl', self._unpack_script(), self.filename]
        mar_scripts = self.mar_scripts
        tools_dir = mar_scripts.tools_dir
        env = tools_environment(tools_dir,
                                mar_scripts.mar_binaries,
                                mar_scripts.env)
        env["MOZ_PKG_PRETTYNAMES"] = self.prettynames
        self.mkdir_p(dst_dir)
        self.run_command(cmd,
                         cwd=dst_dir,
                         env=env,
                         halt_on_failure=True)

    def download(self):
        """downloads mar file - not implemented yet"""
        if not os.path.exists(self.filename):
            pass
        return self.filename

    def _incremental_update_script(self):
        """full path to the incremental update script"""
        scripts = self.mar_scripts
        return scripts.incremental_update

    def _unpack_script(self):
        """returns the full path to the unpack script """
        scripts = self.mar_scripts
        return scripts.unpack

    def incremental_update(self, other, partial_filename):
        """create an incremental update from the current mar to the
          other mar object. It stores the result in partial_filename"""
        fromdir = tempfile.mkdtemp()
        todir = tempfile.mkdtemp()
        self.unpack_mar(fromdir)
        other.unpack_mar(todir)
        # Usage: make_incremental_update.sh [OPTIONS] ARCHIVE FROMDIR TODIR
        cmd = [self._incremental_update_script(), partial_filename,
               fromdir, todir]
        mar_scripts = self.mar_scripts
        tools_dir = mar_scripts.tools_dir
        env = tools_environment(tools_dir,
                                mar_scripts.mar_binaries,
                                mar_scripts.env)
        self.run_command(cmd, cwd=None, env=env)
        self.rmtree(todir)
        self.rmtree(fromdir)

    def buildid(self):
        """returns the buildid of the current mar file"""
        if self.build_id is not None:
            return self.build_id
        temp_dir = tempfile.mkdtemp()
        self.unpack_mar(temp_dir)
        files = self.mar_scripts
        ini_file = os.path.join(temp_dir, files.ini_file)
        # need this chunk to print out the location
        # of the application.ini file.
        # When every platform has it's own application_ini set
        # in the configuration, DELETE the following code.
        # application_ini
        # macosx      [ok]
        # linux 32    [ok]
        # linux 64    [ok]
        # windows     [missing]
        for dirpath, dirnames, filenames in os.walk(temp_dir):
            for f in filenames:
                if f == 'application.ini':
                    self.log("found application.ini file: %s" % os.path.join(dirpath, f))
                    with open(os.path.join(dirpath, f), 'r') as ini:
                        self.log(ini.read())
        #
        self.info("application.ini file: %s" % ini_file)
        self.build_id = buildid_form_ini(ini_file)
        return self.build_id


class MarScripts(object):
    """holds the information on scripts and directories paths needed
       by MarTool and MarFile"""
    def __init__(self, unpack, incremental_update,
                 tools_dir, ini_file, mar_binaries,
                 env):
        self.unpack = unpack
        self.incremental_update = incremental_update
        self.tools_dir = tools_dir
        self.ini_file = ini_file
        self.mar_binaries = mar_binaries
        # what happens in mar.py stays in mar.py
        self.env = copy.deepcopy(env)
