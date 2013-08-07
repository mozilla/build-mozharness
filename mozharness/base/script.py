#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Generic script objects.

script.py, along with config.py and log.py, represents the core of
mozharness.
"""

import codecs
import inspect
import os
import platform
import pprint
import re
import shutil
import socket
import subprocess
import sys
import time
import traceback
import urllib2
import urlparse
if os.name == 'nt':
    try:
        import win32file
        import win32api
        PYWIN32 = True
    except ImportError:
        PYWIN32 = False

try:
    import simplejson as json
    assert json
except ImportError:
    import json

from mozharness.base.config import BaseConfig
from mozharness.base.log import SimpleFileLogger, MultiFileLogger, \
    LogMixin, OutputParser, DEBUG, INFO, ERROR, FATAL


# ScriptMixin {{{1
class ScriptMixin(object):
    """This mixin contains simple filesystem commands and the like.

    It also contains some very special but very complex methods that,
    together with logging and config, provide the base for all scripts
    in this harness.

    Depends on LogMixin and a self.config of some sort.
    """

    env = None

    # Simple filesystem commands {{{2
    def mkdir_p(self, path, error_level=ERROR):
        """
        Returns None for success, not None for failure
        """
        if not os.path.exists(path):
            self.info("mkdir: %s" % path)
            try:
                os.makedirs(path)
            except OSError:
                self.log("Can't create directory %s!" % path,
                         level=error_level)
                return -1
        else:
            self.debug("mkdir_p: %s Already exists." % path)

    def rmtree(self, path, log_level=INFO, error_level=ERROR,
               exit_code=-1):
        """
        Returns None for success, not None for failure
        """
        self.log("rmtree: %s" % path, level=log_level)
        error_message = "Unable to remove %s!" % path
        if self._is_windows():
            # Call _rmtree_windows() directly, since even checking
            # os.path.exists(path) will hang if path is longer than MAX_PATH.
            self.info("Using _rmtree_windows ...")
            return self.retry(
                self._rmtree_windows,
                error_level=error_level,
                error_message=error_message,
                args=(path, ),
            )
        if os.path.exists(path):
            if os.path.isdir(path):
                return self.retry(
                    shutil.rmtree,
                    error_level=error_level,
                    error_message=error_message,
                    retry_exceptions=(OSError, ),
                    args=(path, ),
                )
            else:
                return self.retry(
                    os.remove,
                    error_level=error_level,
                    error_message=error_message,
                    retry_exceptions=(OSError, ),
                    args=(path, ),
                )
        else:
            self.debug("%s doesn't exist." % path)

    def _is_windows(self):
        system = platform.system()
        if system in ("Windows", "Microsoft"):
            return True
        if system.startswith("CYGWIN"):
            return True
        if os.name == 'nt':
            return True

    def query_msys_path(self, path):
        if not isinstance(path, basestring):
            return path
        path = path.replace("\\", "/")

        def repl(m):
            return '/%s/' % m.group(1)
        path = re.sub(r'''^([a-zA-Z]):/''', repl, path)
        return path

    def _rmtree_windows(self, path):
        """ Windows-specific rmtree that handles path lengths longer than MAX_PATH.
            Ported from clobberer.py.
        """
        assert self._is_windows()
        path = os.path.realpath(path)
        full_path = '\\\\?\\' + path
        if not os.path.exists(full_path):
            return
        if not PYWIN32:
            if not os.path.isdir(path):
                return self.run_command('del /F /Q "%s"' % path)
            else:
                return self.run_command('rmdir /S /Q "%s"' % path)
        # Make sure directory is writable
        win32file.SetFileAttributesW('\\\\?\\' + path, win32file.FILE_ATTRIBUTE_NORMAL)
        # Since we call rmtree() with a file, sometimes
        if not os.path.isdir('\\\\?\\' + path):
            return win32file.DeleteFile('\\\\?\\' + path)

        for ffrec in win32api.FindFiles('\\\\?\\' + path + '\\*.*'):
            file_attr = ffrec[0]
            name = ffrec[8]
            if name == '.' or name == '..':
                continue
            full_name = os.path.join(path, name)

            if file_attr & win32file.FILE_ATTRIBUTE_DIRECTORY:
                self._rmtree_windows(full_name)
            else:
                win32file.SetFileAttributesW('\\\\?\\' + full_name, win32file.FILE_ATTRIBUTE_NORMAL)
                win32file.DeleteFile('\\\\?\\' + full_name)
        win32file.RemoveDirectory('\\\\?\\' + path)

    def get_filename_from_url(self, url):
        parsed = urlparse.urlsplit(url.rstrip('/'))
        if parsed.path != '':
            return parsed.path.rsplit('/', 1)[-1]
        else:
            return parsed.netloc

    def _download_file(self, url, file_name):
        """ Helper script for download_file()
            """
        try:
            f = urllib2.urlopen(url, timeout=30)
            local_file = open(file_name, 'wb')
            while True:
                block = f.read(1024 ** 2)
                if not block:
                    break
                local_file.write(block)
            local_file.close()
            return file_name
        except urllib2.HTTPError, e:
            self.warning("Server returned status %s %s for %s" % (str(e.code), str(e), url))
            raise
        except urllib2.URLError, e:
            self.warning("URL Error: %s" % url)
            remote_host = urlparse.urlsplit(url)[1]
            if remote_host:
                nslookup = self.query_exe('nslookup')
                error_list = [{
                    'substr': "server can't find %s" % remote_host,
                    'level': ERROR,
                    'explanation': "Either %s is an invalid hostname, or DNS is busted." % remote_host,
                }]
                self.run_command([nslookup, remote_host],
                                 error_list=error_list)
            raise
        except socket.timeout, e:
            self.warning("Timed out accessing %s: %s" % (url, str(e)))
            raise
        except socket.error, e:
            self.warning("Socket error when accessing %s: %s" % (url, str(e)))
            raise

    # http://www.techniqal.com/blog/2008/07/31/python-file-read-write-with-urllib2/
    # TODO thinking about creating a transfer object.
    def download_file(self, url, file_name=None, parent_dir=None,
                      create_parent_dir=True, error_level=ERROR,
                      exit_code=-1):
        """Python wget.
        """
        if not file_name:
            try:
                file_name = self.get_filename_from_url(url)
            except AttributeError:
                self.log("Unable to get filename from %s; bad url?" % url,
                         level=error_level, exit_code=exit_code)
                return
        if parent_dir:
            file_name = os.path.join(parent_dir, file_name)
            if create_parent_dir:
                self.mkdir_p(parent_dir, error_level=error_level)
        self.info("Downloading %s to %s" % (url, file_name))
        status = self.retry(
            self._download_file,
            args=(url, file_name),
            failure_status=None,
            retry_exceptions=(urllib2.HTTPError, urllib2.URLError,
                              socket.timeout, socket.error),
            error_message="Can't download from %s to %s!" % (url, file_name),
            error_level=error_level,
        )
        if status == file_name:
            self.info("Downloaded %d bytes." % os.path.getsize(file_name))
        return status

    def move(self, src, dest, log_level=INFO, error_level=ERROR,
             exit_code=-1):
        self.log("Moving %s to %s" % (src, dest), level=log_level)
        try:
            shutil.move(src, dest)
        # http://docs.python.org/tutorial/errors.html
        except IOError, e:
            self.log("IO error: %s" % str(e),
                     level=error_level, exit_code=exit_code)
            return -1
        except shutil.Error, e:
            self.log("shutil error: %s" % str(e),
                     level=error_level, exit_code=exit_code)
            return -1
        return 0

    def chmod(self, path, mode):
        self.info("Chmoding %s to %s" % (path, str(oct(mode))))
        os.chmod(path, mode)

    def copyfile(self, src, dest, log_level=INFO, error_level=ERROR, copystat=False):
        self.log("Copying %s to %s" % (src, dest), level=log_level)
        try:
            shutil.copyfile(src, dest)
            if copystat:
                shutil.copystat(src, dest)
        except (IOError, shutil.Error), e:
            self.log("Can't copy %s to %s: %s!" % (src, dest, str(e)),
                     level=error_level)
            return -1

    def copytree(self, src, dest, overwrite='no_overwrite', log_level=INFO,
                 error_level=ERROR):
        """an implementation of shutil.copytree however it allows for
        dest to exist and implements different overwrite levels.
        overwrite uses:
        'no_overwrite' will keep all(any) existing files in destination tree
        'overwrite_if_exists' will only overwrite destination paths that have
                   the same path names relative to the root of the src and
                   destination tree
        'clobber' will replace the whole destination tree(clobber) if it exists"""

        self.info('copying tree: %s to %s' % (src, dest))
        try:
            if overwrite == 'clobber' or not os.path.exists(dest):
                self.rmtree(dest)
                shutil.copytree(src, dest)
            elif overwrite == 'no_overwrite' or overwrite == 'overwrite_if_exists':
                files = os.listdir(src)
                for f in files:
                    abs_src_f = os.path.join(src, f)
                    abs_dest_f = os.path.join(dest, f)
                    if not os.path.exists(abs_dest_f):
                        if os.path.isdir(abs_src_f):
                            self.mkdir_p(abs_dest_f)
                            self.copytree(abs_src_f, abs_dest_f,
                                          overwrite='clobber')
                        else:
                            shutil.copy2(abs_src_f, abs_dest_f)
                    elif overwrite == 'no_overwrite':  # destination path exists
                        if os.path.isdir(abs_src_f) and os.path.isdir(abs_dest_f):
                            self.copytree(abs_src_f, abs_dest_f,
                                          overwrite='no_overwrite')
                        else:
                            self.debug('ignoring path: %s as destination: \
                                    %s exists' % (abs_src_f, abs_dest_f))
                    else:  # overwrite == 'overwrite_if_exists' and destination exists
                        self.debug('overwriting: %s with: %s' %
                                   (abs_dest_f, abs_src_f))
                        self.rmtree(abs_dest_f)

                        if os.path.isdir(abs_src_f):
                            self.mkdir_p(abs_dest_f)
                            self.copytree(abs_src_f, abs_dest_f,
                                          overwrite='overwrite_if_exists')
                        else:
                            shutil.copy2(abs_src_f, abs_dest_f)
            else:
                self.fatal("%s is not a valid argument for param overwrite" % (overwrite))
        except (IOError, shutil.Error):
            self.exception("There was an error while copying %s to %s!" % (src, dest),
                           level=error_level)
            return -1

    def write_to_file(self, file_path, contents, verbose=True,
                      open_mode='w', create_parent_dir=False,
                      error_level=ERROR):
        """
        Write contents to file_path.

        This doesn't currently create the parent_dir or translate into
        abs_path; that needs to be done beforehand, since ScriptMixin doesn't
        necessarily have access to query_abs_dirs().

        Returns file_path if successful, None if not.
        """
        self.info("Writing to file %s" % file_path)
        if verbose:
            self.info("Contents:")
            for line in contents.splitlines():
                self.info(" %s" % line)
        if create_parent_dir:
            parent_dir = os.path.dirname(file_path)
            self.mkdir_p(parent_dir, error_level=error_level)
        try:
            fh = open(file_path, open_mode)
            fh.write(contents)
            fh.close()
            return file_path
        except IOError:
            self.log("%s can't be opened for writing!" % file_path,
                     level=error_level)

    def read_from_file(self, file_path, verbose=True, open_mode='r',
                       error_level=ERROR):
        """
        Reads from file_path.

        Returns contents if successful, None if not.
        """
        self.info("Reading from file %s" % file_path)
        if not os.path.exists(file_path):
            self.log("%s doesn't exist!" % file_path, level=error_level)
            return
        try:
            fh = open(file_path, open_mode)
            contents = fh.read()
            fh.close()
            if verbose:
                self.info("Contents:")
                for line in contents.splitlines():
                    self.info(" %s" % line)
            return contents
        except IOError:
            self.log("%s can't be opened for reading!" % file_path,
                     level=error_level)

    def chdir(self, dir_name):
        self.log("Changing directory to %s." % dir_name)
        os.chdir(dir_name)

    def which(self, program):
        """
        OS independent implementation of Unix's which command
        Takes in a program name
        Returns path to executable or None
        """
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        if self._is_windows() and not program.endswith(".exe"):
            program += ".exe"
        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            env = self.query_env()
            for path in env["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
        return None

    # More complex commands {{{2
    def retry(self, action, attempts=None, sleeptime=60, max_sleeptime=5 * 60,
              retry_exceptions=(Exception, ), good_statuses=None, cleanup=None,
              error_level=ERROR, error_message="%(action)s failed after %(attempts)d tries!",
              failure_status=-1, args=(), kwargs={}):
        """ Generic retry command.
            Ported from tools util.retry.

            Call `action' a maximum of `attempts' times until it succeeds,
            defaulting to self.config.get('global_retries', 5).

            `sleeptime' is the number of seconds to wait between attempts,
            defaulting to 60 and doubling each retry attempt, to a maximum of
            `max_sleeptime'.

            `retry_exceptions' is a tuple of Exceptions that should be caught.
            If exceptions other than those listed in `retry_exceptions' are
            raised from `action', they will be raised immediately.

            `good_statuses' is a tuple of return values which, if specified,
            will result in retrying if the return value isn't listed.

            If `cleanup' is provided and callable it will be called immediately
            after an Exception is caught.  No arguments will be passed to it.
            If your cleanup function requires arguments it is recommended that
            you wrap it in an argumentless function.

            `args' and `kwargs' are a tuple and dict of arguments to pass onto
            to `callable'.
            """
        if not callable(action):
            self.fatal("retry() called with an uncallable method %s!" % action)
        if cleanup and not callable(cleanup):
            self.fatal("retry() called with an uncallable cleanup method %s!" % cleanup)
        if not attempts:
            attempts = self.config.get("global_retries", 5)
        if max_sleeptime < sleeptime:
            self.debug("max_sleeptime %d less than sleeptime %d" % (
                       max_sleeptime, sleeptime))
        n = 0
        while n <= attempts:
            retry = False
            n += 1
            try:
                self.info("retry: Calling %s with args: %s, kwargs: %s, attempt #%d" %
                          (action, str(args), str(kwargs), n))
                status = action(*args, **kwargs)
                if good_statuses and status not in good_statuses:
                    retry = True
            except retry_exceptions, e:
                retry = True
                error_message = "%s\nCaught exception: %s" % (error_message, str(e))

            if not retry:
                return status
            else:
                if cleanup:
                    cleanup()
                if n == attempts:
                    self.log(error_message % {'action': action, 'attempts': n}, level=error_level)
                    return failure_status
                if sleeptime > 0:
                    self.info("retry: Failed, sleeping %d seconds before retrying" %
                              sleeptime)
                    time.sleep(sleeptime)
                    sleeptime = sleeptime * 2
                    if sleeptime > max_sleeptime:
                        sleeptime = max_sleeptime

    def query_env(self, partial_env=None, replace_dict=None,
                  set_self_env=None, log_level=DEBUG):
        """Environment query/generation method.

        The default, self.query_env(), will look for self.config['env']
        and replace any special strings in there ( %(PATH)s ).
        It will then store it as self.env for speeding things up later.

        If you specify partial_env, partial_env will be used instead of
        self.config['env'], and we don't save self.env as it's a one-off.

        """
        if partial_env is None:
            if self.env is not None:
                return self.env
            partial_env = self.config.get('env', None)
            if partial_env is None:
                partial_env = {}
            if set_self_env is None:
                set_self_env = True
        env = os.environ.copy()
        default_replace_dict = self.query_abs_dirs()
        default_replace_dict['PATH'] = os.environ['PATH']
        if not replace_dict:
            replace_dict = default_replace_dict
        else:
            for key in default_replace_dict:
                if key not in replace_dict:
                    replace_dict[key] = default_replace_dict[key]
        for key in partial_env.keys():
            env[key] = partial_env[key] % replace_dict
            self.log("ENV: %s is now %s" % (key, env[key]), level=log_level)
        if set_self_env:
            self.env = env
        return env

    def query_exe(self, exe_name, exe_dict='exes', default=None,
                  return_type=None, error_level=FATAL):
        """One way to work around PATH rewrites.

        By default, return exe_name, and we'll fall through to searching
        os.environ["PATH"].
        However, if self.config[exe_dict][exe_name] exists, return that.
        This lets us override exe paths via config file.

        'return_type' can be None (don't do anything to the value),
        'list' (return a list), or 'string' (return a string).

        If we need runtime setting, we can build in self.exes support later.
        """
        if default is None:
            default = exe_name
        exe = self.config.get(exe_dict, {}).get(exe_name, default)
        repl_dict = {}
        if hasattr(self, 'query_abs_dirs'):
            # allow for 'make': '%(abs_work_dir)s/...' etc.
            dirs = self.query_abs_dirs()
            repl_dict['abs_work_dir'] = dirs['abs_work_dir']
        if isinstance(exe, list):
            exe = [x % repl_dict for x in exe]
        elif isinstance(exe, str):
            exe = exe % repl_dict
        else:
            self.log("query_exe: %s is not a string or list: %s!" % (exe_name, str(exe)), level=error_level)
            return exe
        if return_type == "list":
            if isinstance(exe, str):
                exe = [exe]
        elif return_type == "string":
            if isinstance(exe, list):
                exe = subprocess.list2cmdline(exe)
        elif return_type is not None:
            self.log("Unknown return_type type %s requested in query_exe!" % return_type, level=error_level)
        return exe

    def run_command(self, command, cwd=None, error_list=None,
                    halt_on_failure=False, success_codes=None,
                    env=None, partial_env=None, return_type='status',
                    throw_exception=False, output_parser=None,
                    output_timeout=None):
        """Run a command, with logging and error parsing.

        output_timeout is the number of seconds without output before the process
        is killed; it requires that mozprocess is installed in the script's
        virtualenv.

        TODO: context_lines
        TODO: error_level_override?

        output_parser lets you provide an instance of your own OutputParser
        subclass, or pass None to use OutputParser.

        error_list example:
        [{'regex': re.compile('^Error: LOL J/K'), level=IGNORE},
         {'regex': re.compile('^Error:'), level=ERROR, contextLines='5:5'},
         {'substr': 'THE WORLD IS ENDING', level=FATAL, contextLines='20:'}
        ]
        (context_lines isn't written yet)
        """
        if output_timeout:
            site_packages_path = self.query_python_site_packages_path()
            sys_path = ''.join(sys.path)
            if 'mozprocess' not in sys_path:
                if site_packages_path not in sys_path:
                    # check for mozprocess
                    mozprocess_path = os.path.join(site_packages_path, 'mozprocess')
                    if not os.access(mozprocess_path, os.F_OK):
                        self.fatal('mozprocess required for output_timeout, but not present at %s' % mozprocess_path)
                    # Assume if mozprocess is installed, all it's pre-req's
                    # are present also, and add the top-level site-packages
                    # dir to sys.path.
                    sys.path.append(site_packages_path)

            try:
                from mozprocess import ProcessHandler
            except ImportError:
                self.exception("There was an error importing mozprocess!",
                               level=FATAL)

        if success_codes is None:
            success_codes = [0]
        if cwd is not None:
            if not os.path.isdir(cwd):
                level = ERROR
                if halt_on_failure:
                    level = FATAL
                self.log("Can't run command %s in non-existent directory '%s'!" %
                         (command, cwd), level=level)
                return -1
            self.info("Running command: %s in %s" % (command, cwd))
        else:
            self.info("Running command: %s" % command)
        if isinstance(command, list):
            self.info("Copy/paste: %s" % subprocess.list2cmdline(command))
        shell = True
        if isinstance(command, list):
            shell = False
        if env is None:
            if partial_env:
                self.info("Using partial env: %s" % pprint.pformat(partial_env))
                env = self.query_env(partial_env=partial_env)
        else:
            self.info("Using env: %s" % pprint.pformat(env))

        if output_parser is None:
            parser = OutputParser(config=self.config, log_obj=self.log_obj,
                                  error_list=error_list)
        else:
            parser = output_parser

        try:
            if output_timeout:
                def processOutput(line):
                    parser.add_lines(line)

                p = ProcessHandler(command,
                                   env=env,
                                   cwd=cwd,
                                   storeOutput=False,
                                   processOutputLine=[processOutput])
                p.run(outputTimeout=output_timeout)
                p.wait()
                if p.timedOut:
                    self.error('timed out after %s seconds of no output' % output_timeout)
                returncode = p.proc.returncode
            else:
                p = subprocess.Popen(command, shell=shell, stdout=subprocess.PIPE,
                                     cwd=cwd, stderr=subprocess.STDOUT, env=env)
                loop = True
                while loop:
                    if p.poll() is not None:
                        """Avoid losing the final lines of the log?"""
                        loop = False
                    while True:
                        line = p.stdout.readline()
                        if not line:
                            break
                        parser.add_lines(line)
                returncode = p.returncode
        except OSError, e:
            level = ERROR
            if halt_on_failure:
                level = FATAL
            self.log('caught OS error %s: %s while running %s' % (e.errno,
                     e.strerror, command), level=level)
            return -1

        return_level = INFO
        if returncode not in success_codes:
            return_level = ERROR
            if throw_exception:
                raise subprocess.CalledProcessError(returncode, command)
        self.log("Return code: %d" % returncode, level=return_level)
        if halt_on_failure:
            if parser.num_errors or returncode not in success_codes:
                self.fatal("Halting on failure while running %s" % command,
                           exit_code=returncode)
        if return_type == 'num_errors':
            return parser.num_errors
        return returncode

    def get_output_from_command(self, command, cwd=None,
                                halt_on_failure=False, env=None,
                                silent=False, log_level=INFO,
                                tmpfile_base_path='tmpfile',
                                return_type='output', save_tmpfiles=False,
                                throw_exception=False):
        """Similar to run_command, but where run_command is an
        os.system(command) analog, get_output_from_command is a `command`
        analog.

        Less error checking by design, though if we figure out how to
        do it without borking the output, great.

        TODO: binary mode? silent is kinda like that.
        TODO: since p.wait() can take a long time, optionally log something
        every N seconds?
        TODO: optionally only keep the first or last (N) line(s) of output?
        TODO: optionally only return the tmp_stdout_filename?
        """
        if cwd:
            if not os.path.isdir(cwd):
                level = ERROR
                if halt_on_failure:
                    level = FATAL
                self.log("Can't run command %s in non-existent directory %s!" %
                         (command, cwd), level=level)
                return None
            self.info("Getting output from command: %s in %s" % (command, cwd))
        else:
            self.info("Getting output from command: %s" % command)
        if isinstance(command, list):
            self.info("Copy/paste: %s" % subprocess.list2cmdline(command))
        # This could potentially return something?
        tmp_stdout = None
        tmp_stderr = None
        tmp_stdout_filename = '%s_stdout' % tmpfile_base_path
        tmp_stderr_filename = '%s_stderr' % tmpfile_base_path

        # TODO probably some more elegant solution than 2 similar passes
        try:
            tmp_stdout = open(tmp_stdout_filename, 'w')
        except IOError:
            level = ERROR
            if halt_on_failure:
                level = FATAL
            self.log("Can't open %s for writing!" % tmp_stdout_filename +
                     self.exception(), level=level)
            return None
        try:
            tmp_stderr = open(tmp_stderr_filename, 'w')
        except IOError:
            level = ERROR
            if halt_on_failure:
                level = FATAL
            self.log("Can't open %s for writing!" % tmp_stderr_filename +
                     self.exception(), level=level)
            return None
        shell = True
        if isinstance(command, list):
            shell = False
        p = subprocess.Popen(command, shell=shell, stdout=tmp_stdout,
                             cwd=cwd, stderr=tmp_stderr, env=env)
        #XXX: changed from self.debug to self.log due to this error:
        #     TypeError: debug() takes exactly 1 argument (2 given)
        self.log("Temporary files: %s and %s" % (tmp_stdout_filename, tmp_stderr_filename), level=DEBUG)
        p.wait()
        tmp_stdout.close()
        tmp_stderr.close()
        return_level = DEBUG
        output = None
        if os.path.exists(tmp_stdout_filename) and os.path.getsize(tmp_stdout_filename):
            output = self.read_from_file(tmp_stdout_filename,
                                         verbose=False)
            if not silent:
                self.log("Output received:", level=log_level)
                output_lines = output.rstrip().splitlines()
                for line in output_lines:
                    if not line or line.isspace():
                        continue
                    line = line.decode("utf-8")
                    self.log(' %s' % line, level=log_level)
                output = '\n'.join(output_lines)
        if os.path.exists(tmp_stderr_filename) and os.path.getsize(tmp_stderr_filename):
            return_level = ERROR
            self.error("Errors received:")
            errors = self.read_from_file(tmp_stderr_filename,
                                         verbose=False)
            for line in errors.rstrip().splitlines():
                if not line or line.isspace():
                    continue
                line = line.decode("utf-8")
                self.error(' %s' % line)
        elif p.returncode:
            return_level = ERROR
        # Clean up.
        if not save_tmpfiles:
            self.rmtree(tmp_stderr_filename, log_level=DEBUG)
            self.rmtree(tmp_stdout_filename, log_level=DEBUG)
        if p.returncode and throw_exception:
            raise subprocess.CalledProcessError(p.returncode, command)
        self.log("Return code: %d" % p.returncode, level=return_level)
        if halt_on_failure and return_level == ERROR:
            self.fatal("Halting on failure while running %s" % command,
                       exit_code=p.returncode)
        # Hm, options on how to return this? I bet often we'll want
        # output_lines[0] with no newline.
        if return_type != 'output':
            return (tmp_stdout_filename, tmp_stderr_filename)
        else:
            return output


def PreScriptRun(func):
    """Decorator for methods that will be called before script execution.

    Each method on a BaseScript having this decorator will be called at the
    beginning of BaseScript.run().

    The return value is ignored. Exceptions will abort execution.
    """
    func._pre_run_listener = True
    return func


def PostScriptRun(func):
    """Decorator for methods that will be called after script execution.

    This is similar to PreScriptRun except it is called at the end of
    execution. The method will always be fired, even if execution fails.
    """
    func._post_run_listener = True
    return func


def PreScriptAction(action=None):
    """Decorator for methods that will be called at the beginning of each action.

    Each method on a BaseScript having this decorator will be called during
    BaseScript.run() before an individual action is executed. The method will
    receive the action's name as an argument.

    If no values are passed to the decorator, it will be applied to every
    action. If a string is passed, the decorated function will only be called
    for the action of that name.

    The return value of the method is ignored. Exceptions will abort execution.
    """
    def _wrapped(func):
        func._pre_action_listener = action
        return func

    def _wrapped_none(func):
        func._pre_action_listener = None
        return func

    if type(action) == type(_wrapped):
        return _wrapped_none(action)

    return _wrapped


def PostScriptAction(action=None):
    """Decorator for methods that will be called at the end of each action.

    This behaves similarly to PreScriptAction. It varies in that it is called
    after execution of the action.

    The decorated method will receive the action name as a positional argument.
    It will then receive the following named arguments:

        success - Bool indicating whether the action finished successfully.

    The decorated method will always be called, even if the action threw an
    exception.

    The return value is ignored.
    """
    def _wrapped(func):
        func._post_action_listener = action
        return func

    def _wrapped_none(func):
        func._post_action_listener = None
        return func

    if type(action) == type(_wrapped):
        return _wrapped_none(action)

    return _wrapped


# BaseScript {{{1
class BaseScript(ScriptMixin, LogMixin, object):
    def __init__(self, config_options=None, default_log_level="info", **kwargs):
        super(BaseScript, self).__init__()

        # Collect decorated methods. We simply iterate over the attributes of
        # the current class instance and look for signatures deposited by
        # the decorators.
        self._listeners = dict(
            pre_run=[],
            pre_action=[],
            post_action=[],
            post_run=[],
        )
        for k in dir(self):
            item = getattr(self, k)

            # We only decorate methods, so ignore other types.
            if not inspect.ismethod(item):
                continue

            if hasattr(item, '_pre_run_listener'):
                self._listeners['pre_run'].append(k)

            if hasattr(item, '_pre_action_listener'):
                self._listeners['pre_action'].append((
                    k,
                    item._pre_action_listener))

            if hasattr(item, '_post_action_listener'):
                self._listeners['post_action'].append((
                    k,
                    item._post_action_listener))

            if hasattr(item, '_post_run_listener'):
                self._listeners['post_run'].append(k)

        self.return_code = 0
        self.log_obj = None
        self.abs_dirs = None
        if config_options is None:
            config_options = []
        self.summary_list = []
        self.failures = []
        rw_config = BaseConfig(config_options=config_options,
                               **kwargs)
        self.config = rw_config.get_read_only_config()
        self.actions = tuple(rw_config.actions)
        self.all_actions = tuple(rw_config.all_actions)
        self.env = None
        self.new_log_obj(default_log_level=default_log_level)

        # Set self.config to read-only.
        #
        # We can create intermediate config info programmatically from
        # this in a repeatable way, with logs; this is how we straddle the
        # ideal-but-not-user-friendly static config and the
        # easy-to-write-hard-to-debug writable config.
        #
        # To allow for other, script-specific configurations
        # (e.g., hgtool's buildbot props json parsing), before locking,
        # call self._pre_config_lock().  If needed, this method can
        # alter self.config.
        self._pre_config_lock(rw_config)
        self._config_lock()

        self.info("Run as %s" % rw_config.command_line)

    def _pre_config_lock(self, rw_config):
        """This empty method can allow for config checking and manipulation
        before the config lock, when overridden in scripts.
        """
        pass

    def _config_lock(self):
        """After this point, the config is locked and should not be
        manipulated (based on mozharness.base.config.ReadOnlyDict)
        """
        self.config.lock()

    def _possibly_run_method(self, method_name, error_if_missing=False):
        """This is here for run().
        """
        if hasattr(self, method_name) and callable(getattr(self, method_name)):
            return getattr(self, method_name)()
        elif error_if_missing:
            self.error("No such method %s!" % method_name)

    def copy_logs_to_upload_dir(self):
        """Copies logs to the upload directory"""
        self.info("Copying logs to upload dir...")
        log_files = ['localconfig.json']
        for log_name in self.log_obj.log_files.keys():
            log_files.append(self.log_obj.log_files[log_name])
        dirs = self.query_abs_dirs()
        for log_file in log_files:
            self.copy_to_upload_dir(os.path.join(dirs['abs_log_dir'], log_file),
                                    dest=os.path.join('logs', log_file),
                                    short_desc='%s log' % log_name,
                                    long_desc='%s log' % log_name,
                                    max_backups=self.config.get("log_max_rotate", 0))

    def run_action(self, action):
        if action not in self.actions:
            self.action_message("Skipping %s step." % action)
            return

        method_name = action.replace("-", "_")
        self.action_message("Running %s step." % action)

        # An exception during a pre action listener should abort execution.
        for fn, target in self._listeners['pre_action']:
            if target is not None and target != action:
                continue

            try:
                self.info("Running pre-action listener: %s" % fn)
                method = getattr(self, fn)
                method(action)
            except Exception:
                self.error("Exception during pre-action for %s: %s" % (
                    action, traceback.format_exc()))

                for fn, target in self._listeners['post_action']:
                    if target is not None and target != action:
                        continue

                    try:
                        self.info("Running post-action listener: %s" % fn)
                        method = getattr(self, fn)
                        method(action, success=False)
                    except Exception:
                        self.error("An additional exception occurred during "
                                   "post-action for %s: %s" % (action,
                                   traceback.format_exc()))

                self.fatal("Aborting due to exception in pre-action listener.")

        # We always run post action listeners, even if the main routine failed.
        success = False
        try:
            self.info("Running main action method: %s" % method_name)
            self._possibly_run_method("preflight_%s" % method_name)
            self._possibly_run_method(method_name, error_if_missing=True)
            self._possibly_run_method("postflight_%s" % method_name)
            success = True
        finally:
            post_success = True
            for fn, target in self._listeners['post_action']:
                if target is not None and target != action:
                    continue

                try:
                    self.info("Running post-action listener: %s" % fn)
                    method = getattr(self, fn)
                    method(action, success=success and self.return_code == 0)
                except Exception:
                    post_success = False
                    self.error("Exception during post-action for %s: %s" % (
                        action, traceback.format_exc()))

            if not post_success:
                self.fatal("Aborting due to failure in post-action listener.")

    def run(self):
        """Default run method.
        This is the "do everything" method, based on actions and all_actions.

        First run self.dump_config() if it exists.
        Second, go through the list of all_actions.
        If they're in the list of self.actions, try to run
        self.preflight_ACTION(), self.ACTION(), and self.postflight_ACTION().

        Preflight is sanity checking before doing anything time consuming or
        destructive.

        Postflight is quick testing for success after an action.

        """
        for fn in self._listeners['pre_run']:
            try:
                self.info("Running pre-run listener: %s" % fn)
                method = getattr(self, fn)
                method()
            except Exception:
                self.error("Exception during pre-run listener: %s" %
                           traceback.format_exc())

                for fn in self._listeners['post_run']:
                    try:
                        method = getattr(self, fn)
                        method()
                    except Exception:
                        self.error("An additional exception occurred during a "
                                   "post-run listener: %s" % traceback.format_exc())

                self.fatal("Aborting due to failure in pre-run listener.")

        self.dump_config()
        try:
            for action in self.all_actions:
                self.run_action(action)
        except Exception:
            self.fatal("Uncaught exception: %s" % traceback.format_exc())
        finally:
            post_success = True
            for fn in self._listeners['post_run']:
                try:
                    self.info("Running post-run listener: %s" % fn)
                    method = getattr(self, fn)
                    method()
                except Exception:
                    post_success = False
                    self.error("Exception during post-run listener: %s" %
                               traceback.format_exc())

            if not post_success:
                self.fatal("Aborting due to failure in post-run listener.")

        self.copy_logs_to_upload_dir()

        return self.return_code

    def run_and_exit(self):
        """Runs the script and exits the current interpreter."""
        sys.exit(self.run())

    def clobber(self):
        """
        Delete the working directory
        """
        dirs = self.query_abs_dirs()
        self.rmtree(dirs['abs_work_dir'], error_level=FATAL)

    def query_abs_dirs(self):
        """We want to be able to determine where all the important things
        are.  Absolute paths lend themselves well to this, though I wouldn't
        be surprised if this causes some issues somewhere.

        This should be overridden in any script that has additional dirs
        to query.

        The query_* methods tend to set self.VAR variables as their
        runtime cache.
        """
        if self.abs_dirs:
            return self.abs_dirs
        c = self.config
        dirs = {}
        dirs['base_work_dir'] = c['base_work_dir']
        dirs['abs_work_dir'] = os.path.join(c['base_work_dir'], c['work_dir'])
        dirs['abs_upload_dir'] = os.path.join(dirs['abs_work_dir'], 'upload')
        dirs['abs_log_dir'] = os.path.join(c['base_work_dir'], c.get('log_dir', 'logs'))
        self.abs_dirs = dirs
        return self.abs_dirs

    def dump_config(self, file_path=None, config=None):
        """Dump self.config to localconfig.json
        """
        config = config or self.config
        dirs = self.query_abs_dirs()
        if not file_path:
            file_path = os.path.join(dirs['abs_log_dir'], "localconfig.json")
        self.info("Dumping config to %s." % file_path)
        self.mkdir_p(os.path.dirname(file_path))
        json_config = json.dumps(config, sort_keys=True, indent=4)
        fh = codecs.open(file_path, encoding='utf-8', mode='w+')
        fh.write(json_config)
        fh.close()
        self.info(pprint.pformat(config))

    # logging {{{2
    def new_log_obj(self, default_log_level="info"):
        dirs = self.query_abs_dirs()
        log_config = {
            "logger_name": 'Simple',
            "log_name": 'log',
            "log_dir": dirs['abs_log_dir'],
            "log_level": default_log_level,
            "log_format": '%(asctime)s %(levelname)8s - %(message)s',
            "log_to_console": True,
            "append_to_log": False,
        }
        log_type = self.config.get("log_type", "multi")
        if log_type == "multi":
            log_config['logger_name'] = 'Multi'
        for key in log_config.keys():
            value = self.config.get(key, None)
            if value is not None:
                log_config[key] = value
        if log_type == "multi":
            self.log_obj = MultiFileLogger(**log_config)
        else:
            self.log_obj = SimpleFileLogger(**log_config)

    def action_message(self, message):
        self.info("#####")
        self.info("##### %s" % message)
        self.info("#####")

    def summary(self):
        """Print out all the summary lines added via add_summary()
        throughout the script.

        I'd like to revisit how to do this in a prettier fashion.
        """
        self.action_message("%s summary:" % self.__class__.__name__)
        if self.summary_list:
            for item in self.summary_list:
                try:
                    self.log(item['message'], level=item['level'])
                except ValueError:
                    """log is closed; print as a default. Ran into this
                    when calling from __del__()"""
                    print "### Log is closed! (%s)" % item['message']

    def add_summary(self, message, level=INFO):
        self.summary_list.append({'message': message, 'level': level})
        # TODO write to a summary-only log?
        # Summaries need a lot more love.
        self.log(message, level=level)

    def add_failure(self, key, message="%(key)s failed.", level=ERROR):
        if key not in self.failures:
            self.failures.append(key)
            self.return_code += 1
            self.add_summary(message % {'key': key}, level=level)

    def query_failure(self, key):
        return key in self.failures

    def summarize_success_count(self, success_count, total_count,
                                message="%d of %d successful.",
                                level=None):
        if level is None:
            level = INFO
            if success_count < total_count:
                level = ERROR
        self.add_summary(message % (success_count, total_count),
                         level=level)

    def copy_to_upload_dir(self, target, dest=None, short_desc="unknown",
                           long_desc="unknown", log_level=DEBUG,
                           error_level=ERROR, max_backups=None):
        """Copy target file to upload_dir/dest.

        Potentially update a manifest in the future if we go that route.

        Currently only copies a single file; would be nice to allow for
        recursive copying; that would probably done by creating a helper
        _copy_file_to_upload_dir().

        short_desc and long_desc are placeholders for if/when we add
        upload_dir manifests.
        """
        dirs = self.query_abs_dirs()
        if dest is None:
            dest = os.path.basename(target)
        if dest.endswith('/'):
            dest_file = os.path.basename(target)
            dest_dir = os.path.join(dirs['abs_upload_dir'], dest)
        else:
            dest_file = os.path.basename(dest)
            dest_dir = os.path.join(dirs['abs_upload_dir'], os.path.dirname(dest))
        dest = os.path.join(dest_dir, dest_file)
        if not os.path.exists(target):
            self.log("%s doesn't exist!" % target, level=error_level)
            return None
        self.mkdir_p(dest_dir)
        if os.path.exists(dest):
            if os.path.isdir(dest):
                self.log("%s exists and is a directory!" % dest, level=error_level)
                return -1
            if max_backups:
                # Probably a better way to do this
                oldest_backup = 0
                backup_regex = re.compile("^%s\.(\d+)$" % dest_file)
                for filename in os.listdir(dest_dir):
                    r = backup_regex.match(filename)
                    if r and int(r.groups()[0]) > oldest_backup:
                        oldest_backup = int(r.groups()[0])
                for backup_num in range(oldest_backup, 0, -1):
                    # TODO more error checking?
                    if backup_num >= max_backups:
                        self.rmtree(os.path.join(dest_dir, "%s.%d" % (dest_file, backup_num)),
                                    log_level=log_level)
                    else:
                        self.move(os.path.join(dest_dir, "%s.%d" % (dest_file, backup_num)),
                                  os.path.join(dest_dir, "%s.%d" % (dest_file, backup_num + 1)),
                                  log_level=log_level)
                if self.move(dest, "%s.1" % dest, log_level=log_level):
                    self.log("Unable to move %s!" % dest, level=error_level)
                    return -1
            else:
                if self.rmtree(dest, log_level=log_level):
                    self.log("Unable to remove %s!" % dest, level=error_level)
                    return -1
        self.copyfile(target, dest, log_level=log_level)
        if os.path.exists(dest):
            return dest
        else:
            self.log("%s doesn't exist after copy!" % dest, level=error_level)
            return None


# __main__ {{{1
if __name__ == '__main__':
    pass
