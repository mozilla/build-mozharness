#!/usr/bin/env python
"""Generic script objects.
"""

import codecs
import os
import platform
import pprint
import re
import shutil
import subprocess
import sys
import tempfile
import urllib2

try:
    import json
except:
    import simplejson as json

from mozharness.base.config import BaseConfig
from mozharness.base.log import SimpleFileLogger, MultiFileLogger
from mozharness.base.errors import HgErrorList

# BaseScript {{{1
class BaseScript(object):
    def __init__(self, config_options=None, default_log_level="info", **kwargs):
        self.log_obj = None
        self.abs_dirs = None
        if config_options is None:
            config_options = []
        config_options.extend([[
         ["--multi-log",],
         {"action": "store_const",
          "const": "multi",
          "dest": "log_type",
          "help": "Log using MultiFileLogger"
         }
        ],[
         ["--simple-log",],
         {"action": "store_const",
          "const": "simple",
          "dest": "log_type",
          "help": "Log using SimpleFileLogger"
         }
        ]])
        self.summary_list = []
        rw_config = BaseConfig(config_options=config_options,
                               **kwargs)
        self.config = rw_config.get_read_only_config()
        self.actions = tuple(rw_config.actions)
        self.all_actions = tuple(rw_config.all_actions)
        self.env = None
        self.new_log_obj(default_log_level=default_log_level)
        # self.config is read-only and locked.
        #
        # We can create intermediate config info programmatically from
        # this in a repeatable way, with logs; this is how we straddle the
        # ideal-but-not-user-friendly static config and the
        # easy-to-write-hard-to-debug writable config.
        self._lock_config()
        self.info("Run as %s" % rw_config.command_line)

    def _lock_config(self):
        self.config.lock()

    def _possibly_run_method(self, method_name, error_if_missing=False):
        if hasattr(self, method_name) and callable(getattr(self, method_name)):
            return getattr(self, method_name)()
        elif error_if_missing:
            self.error("No such method %s!" % method_name)

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

        Run self.summary() at the end.

        """
        self.dump_config()
        for action in self.all_actions:
            if action not in self.actions:
                self.action_message("Skipping %s step." % action)
            else:
                method_name = action.replace("-", "_")
                self.action_message("Running %s step." % action)
                self._possibly_run_method("preflight_%s" % method_name)
                self._possibly_run_method(method_name, error_if_missing=True)
                self._possibly_run_method("postflight_%s" % method_name)
        self.summary()

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        c = self.config
        dirs = {}
        dirs['abs_work_dir'] = os.path.join(c['base_work_dir'], c['work_dir'])
        dirs['abs_upload_dir'] = os.path.join(c['base_work_dir'], 'upload_dir')
        if c.get('log_dir', None):
            dirs['abs_log_dir'] = os.path.join(c['base_work_dir'], c['log_dir'])
        else:
            dirs['abs_log_dir'] = os.path.join(dirs['abs_upload_dir'], 'logs')
        self.abs_dirs = dirs
        return self.abs_dirs

    def dump_config(self, file_path=None):
        dirs = self.query_abs_dirs()
        if not file_path:
            file_path = os.path.join(dirs['abs_upload_dir'], "localconfig.json")
        self.info("Dumping config to %s." % file_path)
        self.mkdir_p(dirs['abs_upload_dir'])
        json_config = json.dumps(self.config, sort_keys=True, indent=4)
        fh = codecs.open(file_path, encoding='utf-8', mode='w+')
        fh.write(json_config)
        fh.close()
        self.info(pprint.pformat(self.config))

# os commands {{{2
    def mkdir_p(self, path):
        if not os.path.exists(path):
            self.info("mkdir: %s" % path)
            if not self.config['noop']:
                os.makedirs(path)
        else:
            self.debug("mkdir_p: %s Already exists." % path)

    def rmtree(self, path, error_level='error', exit_code=-1):
        self.info("rmtree: %s" % path)
        if os.path.exists(path):
            if not self.config['noop']:
                if os.path.isdir(path):
                    if self._is_windows():
                        self._rmdir_recursive(path)
                    else:
                        shutil.rmtree(path)
                else:
                    os.remove(path)
                if os.path.exists(path):
                    self.log('Unable to remove %s!' % path, level=error_level,
                             exit_code=exit_code)
        else:
            self.debug("%s doesn't exist." % path)

    def _is_windows(self):
        if platform.system() in ("Windows",):
            return True
        if platform.system().startswith("CYGWIN"):
            return True

    def _rmdir_recursive(self, path):
        """This is a replacement for shutil.rmtree that works better under
        windows. Thanks to Bear at the OSAF for the code."""
        if not os.path.exists(path):
            return

        # Verify the directory is read/write/execute for the current user
        os.chmod(path, 0700)

        for name in os.listdir(path):
            full_name = os.path.join(path, name)
            # on Windows, if we don't have write permission we can't remove
            # the file/directory either, so turn that on
            if self._is_windows():
                if not os.access(full_name, os.W_OK):
                    # I think this is now redundant, but I don't have an NT
                    # machine to test on, so I'm going to leave it in place
                    # -warner
                    os.chmod(full_name, 0600)
            if os.path.islink(full_name):
                os.remove(full_name) # as suggested in bug #792
            elif os.path.isdir(full_name):
                self._rmdir_recursive(full_name)
            else:
                if os.path.isfile(full_name):
                    os.chmod(full_name, 0700)
                os.remove(full_name)
        os.rmdir(path)

    # http://www.techniqal.com/blog/2008/07/31/python-file-read-write-with-urllib2/
    def download_file(self, url, file_name=None,
                     error_level='error', exit_code=-1):
        """Python wget.
        TODO: option to mkdir_p dirname(file_name) if it doesn't exist.
        TODO: should noop touch the filename? seems counter-noop.
        """
        if not file_name:
            file_name = os.path.basename(url)
        if self.config['noop']:
            self.info("Downloading %s" % url)
            return file_name
        req = urllib2.Request(url)
        try:
            self.info("Downloading %s" % url)
            f = urllib2.urlopen(req)
            local_file = open(file_name, 'w')
            local_file.write(f.read())
            local_file.close()
        except urllib2.HTTPError, e:
            self.log("HTTP Error: %s %s" % (e.code, url), level=error_level,
                     exit_code=exit_code)
            return
        except urllib2.URLError, e:
            self.log("URL Error: %s" % (url), level=error_level,
                     exit_code=exit_code)
            return
        return file_name

    def move(self, src, dest):
        self.info("Moving %s to %s" % (src, dest))
        if not self.config['noop']:
            shutil.move(src, dest)

    def chmod(self, path, mode):
        self.info("Chmoding %s to %s" % (path, mode))
        if not self.config['noop']:
            os.chmod(path, mode)

    def chown(self, path, uid, guid):
        self.info("Chowning %s to uid %s guid %s" % (path, uid, guid))
        if not self.config['noop']:
            os.chown(path, uid, guid)

    def copyfile(self, src, dest, error_level='error'):
        self.info("Copying %s to %s" % (src, dest))
        if not self.config['noop']:
            try:
                shutil.copyfile(src, dest)
            except:
                # TODO say why
                self.log("Can't copy %s to %s!" % (src, dest),
                         level=error_level)

    def chdir(self, dir_name, ignore_if_noop=False):
        self.log("Changing directory to %s." % dir_name)
        if self.config['noop'] and ignore_if_noop:
            self.info("noop: not changing dir")
        else:
            os.chdir(dir_name)

# logging {{{2
    def new_log_obj(self, default_log_level="info"):
        dirs = self.query_abs_dirs()
        log_config = {"logger_name": 'Simple',
                      "log_name": 'test',
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
            raise SystemExit(exit_code)

    def debug(self, message):
        if self.config.get('log_level', None) == 'debug':
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

    def action_message(self, message):
        self.info("#####")
        self.info("##### %s" % message)
        self.info("#####")

    def summary(self):
        self.action_message("%s summary:" % self.__class__.__name__)
        if self.summary_list:
            for item in self.summary_list:
                try:
                    self.log(item['message'], level=item['level'])
                except ValueError:
                    """log is closed; print as a default. Ran into this
                    when calling from __del__()"""
                    print "### Log is closed! (%s)" % item['message']

    def add_summary(self, message, level='info'):
        self.summary_list.append({'message': message, 'level': level})
        # TODO write to a summary-only log?
        # Summaries need a lot more love.
        self.log(message, level=level)

# run_command and get_output_from_command {{{2
    """These are very special but very complex methods that, together with
    logging and config, provide the base for all scripts in this harness.
    """

    def query_env(self, partial_env=None, replace_dict=None):
        """Environment query/generation method.

        The default, self.query_env(), will look for self.config['env']
        and replace any special strings in there ( %(PATH)s ).
        It will then store it as self.env for speeding things up later.

        If you specify partial_env, partial_env will be used instead of
        self.config['env'], and we don't save self.env as it's a one-off.

        """
        set_self_env = False
        if partial_env is None:
            if self.env:
                return self.env
            set_self_env = True
            partial_env = self.config.get('env', None)
            if not partial_env:
                return None
        env = os.environ.copy()
        if replace_dict is None:
            replace_dict = {}
        replace_dict['PATH'] = os.environ['PATH']
        for key in partial_env.keys():
            env[key] = partial_env[key] % replace_dict
            self.debug("ENV: %s is now %s" % (key, env[key]))
        if set_self_env:
            self.env = env
        return env

    def run_command(self, command, cwd=None, error_list=[], parse_at_end=False,
                    shell=True, halt_on_failure=False, success_codes=[0],
                    env=None, return_type='status'):
        """Run a command, with logging and error parsing.

        TODO: parse_at_end, contextLines
        TODO: retry_interval?
        TODO: error_level_override?
        TODO: command should be able to be a list or a string.
              If it's a list, I would want a copy-pasteable version of it
              output in the log at some point; this would need to be
              properly formatted (so ['echo', 'foo'] would not be
                INFO - Running Command: echo foo
              but
                INFO - Running Command: 'echo' 'foo'
              )
              This'll be even trickier if the contents of the list have
              single quotes in them.

        error_list example:
        [{'regex': '^Error: LOL J/K', level='ignore'},
         {'regex': '^Error:', level='error', contextLines='5:5'},
         {'substr': 'THE WORLD IS ENDING', level='fatal', contextLines='20:'}
        ]
        """
        if return_type == 'output':
            return self.get_output_from_command(command=command, cwd=cwd,
                                                shell=shell,
                                                halt_on_failure=halt_on_failure,
                                                env=env)
        num_errors = 0
        if cwd:
            if not os.path.isdir(cwd):
                self.error("Can't run command %s in non-existent directory %s!" % \
                           (command, cwd))
                return -1
            self.info("Running command: %s in %s" % (command, cwd))
        else:
            self.info("Running command: %s" % command)
        if self.config['noop']:
            self.info("(Dry run; skipping)")
            return
        p = subprocess.Popen(command, shell=shell, stdout=subprocess.PIPE,
                             cwd=cwd, stderr=subprocess.STDOUT, env=env)
        loop = True
        while loop:
            if p.poll() is not None:
                """Avoid losing the final lines of the log?"""
                loop = False
            for line in p.stdout:
                if not line or line.isspace():
                    continue
                line = line.decode("utf-8").rstrip()
                for error_check in error_list:
                    match = False
                    if 'substr' in error_check:
                        if error_check['substr'] in line:
                            match = True
                    elif 'regex' in error_check:
                        if re.search(error_check['regex'], line):
                            match = True
                    else:
                        self.warn("error_list: 'substr' and 'regex' not in %s" % \
                                  error_check)
                    if match:
                        level=error_check.get('level', 'info')
                        self.log(' %s' % line, level=level)
                        if level in ('error', 'critical', 'fatal'):
                            num_errors = num_errors + 1
                        break
                else:
                    self.info(' %s' % line)
        return_level = 'info'
        if p.returncode not in success_codes:
            return_level = 'error'
        self.log("Return code: %d" % p.returncode, level=return_level)
        if halt_on_failure:
            if num_errors or p.returncode not in success_codes:
                self.fatal("Halting on failure while running %s" % command,
                           exit_code=p.returncode)
        if return_type == 'num_errors':
            return num_errors
        return p.returncode

    def get_output_from_command(self, command, cwd=None, shell=True,
                                halt_on_failure=False, env=None,
                                silent=False):
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
                self.error("Can't run command %s in non-existent directory %s!" % \
                           (command, cwd))
                return -1
            self.info("Getting output from command: %s in %s" % (command, cwd))
        else:
            self.info("Getting output from command: %s" % command)
        # This could potentially return something?
        if self.config['noop']:
            self.info("(Dry run; skipping)")
            return
        tmp_stdout = None
        tmp_stderr = None
        pv = platform.python_version_tuple()
        python_26 = False
        # Bad NamedTemporaryFile in python_version < 2.6 :(
        if int(pv[0]) > 2 or (int(pv[0]) == 2 and int(pv[1]) >= 6):
            python_26 = True
            tmp_stdout = tempfile.NamedTemporaryFile(suffix="stdout",
                                                     delete=False)
            tmp_stderr = tempfile.NamedTemporaryFile(suffix="stderr",
                                                     delete=False)
        else:
            tmp_stdout = tempfile.NamedTemporaryFile(suffix="stdout")
            tmp_stderr = tempfile.NamedTemporaryFile(suffix="stderr")
        tmp_stdout_filename = tmp_stdout.name
        tmp_stderr_filename = tmp_stderr.name
        p = subprocess.Popen(command, shell=shell, stdout=tmp_stdout,
                             cwd=cwd, stderr=tmp_stderr, env=env)
        self.debug("Temporary files: %s and %s" % (tmp_stdout_filename, tmp_stderr_filename))
        p.wait()
        return_level = 'debug'
        output = None
        if os.path.exists(tmp_stdout_filename) and os.path.getsize(tmp_stdout_filename):
            fh = open(tmp_stdout_filename)
            output = fh.read()
            if not silent:
                self.info("Output received:")
                output_lines = output.rstrip().splitlines()
                for line in output_lines:
                    if not line or line.isspace():
                        continue
                    line = line.decode("utf-8")
                    self.info(' %s' % line)
                output = '\n'.join(output_lines)
        if os.path.exists(tmp_stderr_filename) and os.path.getsize(tmp_stderr_filename):
            return_level = 'error'
            self.error("Errors received:")
            fh = open(tmp_stderr_filename)
            errors = fh.read()
            for line in errors.rstrip().splitlines():
                if not line or line.isspace():
                    continue
                line = line.decode("utf-8")
                self.error(' %s' % line)
            fh.close()
        elif p.returncode:
            return_level = 'error'
        self.log("Return code: %d" % p.returncode, level=return_level)
        if python_26:
            self.rmtree(tmp_stdout_filename)
            self.rmtree(tmp_stderr_filename)
        if halt_on_failure and return_level == 'error':
            self.fatal("Halting on failure while running %s" % command,
                       exit_code=p.returncode)
        # Hm, options on how to return this? I bet often we'll want
        # output_lines[0] with no newline.
        return output
# End run_command and get_output_from_command 2}}}



# Mercurial {{{1
"""If we ever support multiple vcs, this could potentially go into a
source.py or source/mercurial.py so script.py doesn't end up like factory.py.

This should be rewritten to work closely with Catlee's hgtool.
"""
class MercurialMixin(object):
    """This should eventually just use catlee's hg libs."""

    #TODO: num_retries
    def scm_checkout(self, repo, parent_dir=None, tag="default",
                     dir_name=None, clobber=False, halt_on_failure=True):
        if not dir_name:
            dir_name = os.path.basename(repo)
        if parent_dir:
            dir_path = os.path.join(parent_dir, dir_name)
            self.mkdir_p(parent_dir)
        else:
            dir_path = dir_name
        if clobber and os.path.exists(dir_path):
            self.rmtree(dir_path)
        if not os.path.exists(dir_path):
            command = "hg clone %s %s" % (repo, dir_name)
        else:
            command = "hg --cwd %s pull" % (dir_name)
        self.run_command(command, cwd=parent_dir, halt_on_failure=halt_on_failure,
                        error_list=HgErrorList)
        self.scm_update(dir_path, tag=tag, halt_on_failure=halt_on_failure)

    def scm_update(self, dir_path, tag="default", halt_on_failure=True):
        command = "hg --cwd %s update -C -r %s" % (dir_path, tag)
        self.run_command(command, halt_on_failure=halt_on_failure,
                        error_list=HgErrorList)

    def scm_checkout_repos(self, repo_list, parent_dir=None,
                           clobber=False, halt_on_failure=True):
        c = self.config
        if not parent_dir:
            parent_dir = os.path.join(c['base_work_dir'], c['work_dir'])
        self.mkdir_p(parent_dir)
        for repo_dict in repo_list:
            kwargs = repo_dict.copy()
            kwargs['parent_dir'] = parent_dir
            kwargs['clobber'] = clobber
            kwargs['halt_on_failure'] = halt_on_failure
            self.scm_checkout(**kwargs)

class MercurialScript(MercurialMixin, BaseScript):
    def __init__(self, **kwargs):
        super(MercurialScript, self).__init__(**kwargs)
        
        


# __main__ {{{1
if __name__ == '__main__':
    pass
