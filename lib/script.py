#!/usr/bin/env python
"""Generic script objects.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib2

from config import BaseConfig
from log import SimpleFileLogger, MultiFileLogger
from errors import HgErrorRegexList

# BaseScript {{{1
class BaseScript(object):
    def __init__(self, config_options=None, default_log_level="info", **kwargs):
        if config_options is None:
            config_options = []
        else:
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
        self.summaryList = []
        rw_config = BaseConfig(config_options=config_options, **kwargs)
        self.config = rw_config.getReadOnlyConfig()
        self.actions = tuple(rw_config.actions)
        self.newLogObj(default_log_level=default_log_level)
        """I can definitely see wanting to get more runtime info before
        locking -- what's my hg revision? What's the latest ____
        in this json feed?  ... that you might want to save for later
        for a respin.  But as I think of what I'd want to add
        to this list, I keep thinking of more and more things.

        Now I'm thinking it's two steps: 1) figure out runtime details;
        2) set up configs and run.  (2) can be iterated over multiple
        times during respins. (1) should be external to that."""
        self.__lockConfig()
        self.info("Run as %s" % rw_config.command_line)

    def __lockConfig(self):
        self.config.lock()

    def newLogObj(self, default_log_level="info"):
        log_config = {"logger_name": 'Simple',
                      "log_name": 'test',
                      "log_dir": 'logs',
                      "log_level": default_log_level,
                      "log_format": '%(asctime)s - %(levelname)s - %(message)s',
                      "log_to_console": True,
                      "append_to_log": False,
                     }
        log_type = self.config.get("log_type", None)
        if log_type == "multi":
            log_config['logger_name'] = 'Multi'
        for key in log_config.keys():
            value = self.config.get(key, None)
            if value:
                log_config[key] = value
        if log_type == "multi":
            self.log_obj = MultiFileLogger(**log_config)
        else:
            self.log_obj = SimpleFileLogger(**log_config)

    def summary(self):
        if self.summaryList:
            self.info("#####\n##### %s summary:\n#####" % self.__class__.__name__)
            for item in self.summaryList:
                try:
                    self.log(item['message'], level=item['level'])
                except ValueError:
                    """log is closed; print as a default. Ran into this
                    when calling from __del__()"""
                    print "### Log is closed! (%s)" % item['message']

    def addSummary(self, message, level='info'):
        self.summaryList.append({'message': message, 'level': level})
        # TODO write to a summary-only log?
        self.log(message, level=level)

    def mkdir_p(self, path):
        self.info("mkdir: %s" % path)
        if not os.path.exists(path):
            os.makedirs(path)
        else:
            self.info("Already exists.")

    def rmtree(self, path, error_level='error', exit_code=-1):
        self.info("rmtree: %s" % path)
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            if os.path.exists(path):
                self.log('Unable to remove %s!' % path, level=error_level,
                         exit_code=exit_code)
        else:
            self.debug("%s doesn't exist." % path)

    # http://www.techniqal.com/blog/2008/07/31/python-file-read-write-with-urllib2/
    def downloadFile(self, url, file_name=None, test_only=False,
                     error_level='error', exit_code=-1):
        """Python wget.
        TODO: option to mkdir_p dirname(file_name) if it doesn't exist.
        """
        if not file_name:
            file_name = os.path.basename(url)
        if test_only:
            self.info("Touching %s instead of downloading..." % file_name)
            os.system("touch %s" % file_name)
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
            self.log("URL Error: %s %s" % (e.code, url), level=error_level,
                       exit_code=exit_code)
            return
        return file_name

    def move(self, src, dest):
        self.info("Moving %s to %s" % (src, dest))
        shutil.move(src, dest)

    def copyfile(self, src, dest):
        self.info("Copying %s to %s" % (src, dest))
        shutil.copyfile(src, dest)

    def chdir(self, dir_name):
        self.log("Changing directory to %s." % dir_name)
        os.chdir(dir_name)

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

# runCommand and getOutputFromCommand {{{2
    """These are very special but very complex methods that, together with
    logging and config, provide the base for all scripts in this harness.
    """
    def runCommand(self, command, cwd=None, error_regex_list=[], parse_at_end=False,
                   shell=True, halt_on_failure=False, success_codes=[0],
                   env=None, returnType='status'):
        """Run a command, with logging and error parsing.

        TODO: parse_at_end, contextLines
        TODO: retry_interval?
        TODO: error_level_override?

        error_regex_list example:
        [{'regex': '^Error: LOL J/K', level='ignore'},
         {'regex': '^Error:', level='error', contextLines='5:5'},
         {'substr': 'THE WORLD IS ENDING', level='fatal', contextLines='20:'}
        ]
        """
        if returnType != 'status':
            return self.getOutputFromCommand(command=command, cwd=cwd,
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
                for error_check in error_regex_list:
                    match = False
                    if 'substr' in error_check:
                        if error_check['substr'] in line:
                            match = True
                    elif 'regex' in error_check:
                        if re.search(error_check['regex'], line):
                            match = True
                    else:
                        self.warn("error_regex_list: 'substr' and 'regex' not in %s" % \
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
        return p.returncode

    def getOutputFromCommand(self, command, cwd=None, shell=True,
                             halt_on_failure=False, env=None, silent=False):
        """Similar to runCommand, but where runCommand is an
        os.system(command) analog, getOutputFromCommand is a `command`
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
        tmp_stdout = tempfile.NamedTemporaryFile(suffix="stdout", delete=False)
        tmp_stdout_filename = tmp_stdout.name
        tmp_stderr = tempfile.NamedTemporaryFile(suffix="stderr", delete=False)
        tmp_stderr_filename = tmp_stderr.name
        p = subprocess.Popen(command, shell=shell, stdout=tmp_stdout,
                             cwd=cwd, stderr=tmp_stderr, env=env)
        self.debug("Temporary files: %s and %s" % (tmp_stdout_filename, tmp_stderr_filename))
        p.wait()
        return_level = 'error'
        output = None
        if os.path.exists(tmp_stdout_filename) and os.path.getsize(tmp_stdout_filename):
            if not return_level:
                return_level = 'info'
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
        self.rmtree(tmp_stdout_filename)
        self.rmtree(tmp_stderr_filename)
        if halt_on_failure and return_level == 'error':
            self.fatal("Halting on failure while running %s" % command,
                       exit_code=p.returncode)
        # Hm, options on how to return this? I bet often we'll want
        # output_lines[0] with no newline.
        return output
# End runCommand and getOutputFromCommand 2}}}



# Mercurial {{{1
"""If we ever support multiple vcs, this could potentially go into a
source.py so script.py doesn't end up like factory.py.
"""
class AbstractMercurialScript(object):
    """This should eventually just use catlee's hg libs."""
    def __init__(self):
        """Quick 'n' dirty "Don't clone me; inherit me"
        """
        assert None

    def rmtree(self, **kwargs):
        """For pylint."""
        pass

    #TODO: num_retries
    def scmCheckout(self, hg_repo, parent_dir=None, tag="default",
                     dir_name=None, clobber=False, halt_on_failure=True):
        if not dir_name:
            dir_name = os.path.basename(hg_repo)
        if parent_dir:
            dir_path = os.path.join(parent_dir, dir_name)
        else:
            dir_path = dir_name
        if clobber and os.path.exists(dir_path):
            self.rmtree(dir_path)
        if not os.path.exists(dir_path):
            command = "hg clone %s %s" % (hg_repo, dir_name)
        else:
            command = "hg --cwd %s pull" % (dir_name)
        self.runCommand(command, cwd=parent_dir, halt_on_failure=halt_on_failure,
                        error_regex_list=HgErrorRegexList)
        self.scmUpdate(dir_path, tag=tag, halt_on_failure=halt_on_failure)

    def scmUpdate(self, dir_path, tag="default", halt_on_failure=True):
        command = "hg --cwd %s update -C -r %s" % (dir_path, tag)
        self.runCommand(command, halt_on_failure=halt_on_failure,
                        error_regex_list=HgErrorRegexList)

class MercurialScript(BaseScript, AbstractMercurialScript):
    def __init__(self, **kwargs):
        BaseScript.__init__(self, **kwargs)
        
        


# __main__ {{{1
if __name__ == '__main__':
    obj = BaseScript(initial_config_file=os.path.join('test', 'test.json'),
                     default_log_level="debug")
    obj.runCommand("find .")
    obj.rmtree("test_logs")
