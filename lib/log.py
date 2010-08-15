#!/usr/bin/env python
"""Generic logging, the way I remember it from scripts gone by.

TODO:
- network logging support.
- ability to change log settings mid-stream
- per-module log settings
- are we really forced to use global logging.* settings???
  - i hope i'm mistaken here
  - would love to do instance-based settings so we can have multiple
    objects that can each have their own logger
- ability to queryConfig/queryVar from here
  - log rotation config
  - general "echo-don't-execute" flag that gets every destructive method in
    BasicFunctions to echo only
"""

from datetime import datetime
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib2

# Define our own FATAL
FATAL = logging.CRITICAL + 10
logging.addLevelName(FATAL, 'FATAL')



# ErrorRegexes {{{1

# For ssh, scp, rsync over ssh
SSHErrorRegexList=[{'substr': 'Name or service not known', 'level': 'error'},
                   {'substr': 'Could not resolve hostname', 'level': 'error'},
                   {'substr': 'POSSIBLE BREAK-IN ATTEMPT', 'level': 'warning'},
                   {'substr': 'Network error:', 'level': 'error'},
                   {'substr': 'Access denied', 'level': 'error'},
                   {'substr': 'Authentication refused', 'level': 'error'},
                   {'substr': 'Out of memory', 'level': 'error'},
                   {'substr': 'Connection reset by peer', 'level': 'warning'},
                   {'substr': 'Host key verification failed', 'level': 'error'},
                   {'substr': 'command not found', 'level': 'error'},
                   {'substr': 'WARNING:', 'level': 'warning'},
                   {'substr': 'rsync error:', 'level': 'error'},
                   {'substr': 'Broken pipe:', 'level': 'error'},
                   {'substr': 'connection unexpectedly closed:', 'level': 'error'},
                  ]

HgErrorRegexList=[{'regex': '^abort:', 'level': 'error'},
                  {'substr': 'command not found', 'level': 'error'},
                  {'substr': 'unknown exception encountered', 'level': 'error'},
                 ]

PythonErrorRegexList=[{'substr': 'Traceback (most recent call last)', 'level': 'error'},
                      {'substr': 'SyntaxError: ', 'level': 'error'},
                      {'substr': 'TypeError: ', 'level': 'error'},
                      {'substr': 'NameError: ', 'level': 'error'},
                      {'substr': 'ZeroDivisionError: ', 'level': 'error'},
                      {'substr': 'command not found', 'level': 'error'},
                     ]




# BasicFunctions {{{1
class BasicFunctions(object):
    """This class won't work without also inheriting a Log object.
    I suppose I could create stub info() etc. functions if that's
    a want.
    """
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
            file_name = os.basename(url)
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



# BaseLogger {{{1
class BaseLogger(object):
    """Create a base logging class.
    TODO: status? There may be a status object or status capability in
    either logging or config that allows you to count the number of
    error,critical,fatal messages for us to count up at the end (aiming
    for 0).

    This "warning" instead of "warn" is going to trip me up.
    (It has, already.)
    However, while adding a 'warn': logging.WARNING would be nice,

        a) I don't want to confuse people who know the logging module and
           are comfortable with WARNING, so removing 'warning' is out, and
        b) there's a |for level in self.LEVELS.keys():| below, which would
           create a dup .warn.log alongside the .warning.log.
    """
    LEVELS = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL,
              'fatal': FATAL
             }

    def __init__(self, log_level='info',
                 log_format='%(message)s',
                 log_date_format='%H:%M:%S',
                 log_name='test',
                 log_to_console=True,
                 log_dir='.',
                 log_to_raw=False,
                 logger_name='',
                 halt_on_failure=True,
                 append_to_log=False,
                ):
        self.halt_on_failure = halt_on_failure,
        self.log_format = log_format
        self.log_date_format = log_date_format
        self.log_to_console = log_to_console
        self.log_to_raw = log_to_raw
        self.log_level = log_level
        self.log_name = log_name
        self.log_dir = log_dir
        self.append_to_log = append_to_log

        # Not sure what I'm going to use this for; useless unless we
        # can have multiple logging objects that don't trample each other
        self.logger_name = logger_name

        self.all_handlers = []
        self.log_files = {}

        self.createLogDir()

    def createLogDir(self):
        if os.path.exists(self.log_dir):
            if not os.path.isdir(self.log_dir):
                os.remove(self.log_dir)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.abs_log_dir = os.path.abspath(self.log_dir)

    def initMessage(self, name=None):
        if not name:
            name = self.__class__.__name__
        self.info("%s online at %s in %s" % \
                  (name, datetime.now().strftime("%Y%m%d %H:%M:%S"),
                   os.getcwd()))

    def getLoggerLevel(self, level=None):
        if not level:
            level = self.log_level
        return self.LEVELS.get(level, logging.NOTSET)

    def getLogFormatter(self, log_format=None, date_format=None):
        if not log_format:
            log_format = self.log_format
        if not date_format:
            date_format = self.log_date_format
        return logging.Formatter(log_format, date_format)

    def newLogger(self, logger_name):
        """Create a new logger.
        By default there are no handlers.
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(self.getLoggerLevel())
        self._clearHandlers()
        if self.log_to_console:
            self.addConsoleHandler()
        if self.log_to_raw:
            self.log_files['raw'] = '%s_raw.log' % self.log_name
            self.addFileHandler(os.path.join(self.abs_log_dir,
                                             self.log_files['raw']),
                                log_format='%(message)s')

    def _clearHandlers(self):
        """To prevent dups -- logging will preserve Handlers across
        objects :(
        """
        attrs = dir(self)
        if 'all_handlers' in attrs and 'logger' in attrs:
            for handler in self.all_handlers:
                self.logger.removeHandler(handler)
            self.all_handlers = []

    def __del__(self):
        self._clearHandlers()

    def addConsoleHandler(self, log_level=None, log_format=None,
                          date_format=None):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.getLoggerLevel(log_level))
        console_handler.setFormatter(self.getLogFormatter(log_format=log_format,
                                                         date_format=date_format))
        self.logger.addHandler(console_handler)
        self.all_handlers.append(console_handler)

    def addFileHandler(self, log_path, log_level=None, log_format=None,
                       date_format=None):
        if not self.append_to_log and os.path.exists(log_path):
            os.remove(log_path)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(self.getLoggerLevel(log_level))
        file_handler.setFormatter(self.getLogFormatter(log_format=log_format,
                                                      date_format=date_format))
        self.logger.addHandler(file_handler)
        self.all_handlers.append(file_handler)

    def log(self, message, level='info', exit_code=-1):
        """Generic log method.
        There should be more options here -- do or don't split by line,
        use os.linesep instead of assuming \n, be able to pass in log level
        by name or number.

        Adding the "ignore" special level for runCommand.
        """
        if level == "ignore":
            return
        for line in message.splitlines():
            self.logger.log(self.getLoggerLevel(level), line)
        if level == 'fatal' and self.halt_on_failure:
            self.logger.log(FATAL, 'Exiting %d' % exit_code)
            sys.exit(exit_code)

    def debug(self, message):
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


# SimpleFileLogger {{{1
class SimpleFileLogger(BaseLogger):
    """Create one logFile.  Possibly also output to
    the terminal and a raw log (no prepending of level or date)
    """
    def __init__(self,
                 log_format='%(asctime)s - %(levelname)s - %(message)s',
                 logger_name='Simple', log_dir='logs', **kwargs):
        BaseLogger.__init__(self, logger_name=logger_name, log_format=log_format,
                            log_dir=log_dir, **kwargs)
        self.newLogger(self.logger_name)
        self.initMessage()

    def newLogger(self, logger_name):
        BaseLogger.newLogger(self, logger_name)
        self.log_path = os.path.join(self.abs_log_dir, '%s.log' % self.log_name)
        self.log_files['default'] = self.log_path
        self.addFileHandler(self.log_path)




# MultiFileLogger {{{1
class MultiFileLogger(BaseLogger):
    """Create a log per log level in log_dir.  Possibly also output to
    the terminal and a raw log (no prepending of level or date)
    """
    def __init__(self, logger_name='Multi',
                 log_format='%(asctime)s - %(levelname)s - %(message)s',
                 log_dir='logs', log_to_raw=True, **kwargs):
        BaseLogger.__init__(self, logger_name=logger_name, log_format=log_format,
                            log_to_raw=log_to_raw, log_dir=log_dir,
                            **kwargs)

        self.newLogger(self.logger_name)
        self.initMessage()

    def newLogger(self, logger_name):
        BaseLogger.newLogger(self, logger_name)
        minLoggerLevel = self.getLoggerLevel(self.log_level)
        for level in self.LEVELS.keys():
            if self.getLoggerLevel(level) >= minLoggerLevel:
                self.log_files[level] = '%s_%s.log' % (self.log_name,
                                                      level)
                self.addFileHandler(os.path.join(self.abs_log_dir,
                                                 self.log_files[level]),
                                    log_level=level)



# __main__ {{{1

if __name__ == '__main__':
    """Quick 'n' dirty unit tests.
    Ideally, this would be parsed automatically, too, and wouldn't leave
    cruft behind.
    """
    def testLogger(obj):
        obj.log('YOU SHOULD NOT SEE THIS LINE', level='debug')
        for level in ('info', 'warning', 'error', 'critical'):
            obj.log('test %s' % level, level=level)
        try:
            obj.log('test fatal -- you should see an exit line after this.',
                    level='fatal')
        except:
            print "Yay, that's good."
        else:
            print "OH NO!"

    log_dir = 'test_logs'
    obj = MultiFileLogger(log_level='info', log_dir=log_dir,
                          log_to_raw=True)
    testLogger(obj)
    obj.halt_on_failure=False
    obj.log('test fatal -- you should *not* see an exit line after this.',
            level='fatal')
    obj = SimpleFileLogger(log_dir=log_dir)
    testLogger(obj)
    print "=========="
    print "You should be able to examine %s." % log_dir
