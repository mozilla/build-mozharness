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
- log rotation
- per-runCommand-haltOnFailure in BasicFunctions
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
import urllib2

# Define our own FATAL
FATAL = logging.CRITICAL + 10
logging.addLevelName(FATAL, 'FATAL')



# ErrorRegexes {{{1

# For ssh, scp, rsync over ssh
SshErrorRegex=[{'regex': 'Name or service not known', 'level': 'error'},
               {'regex': 'Could not resolve hostname', 'level': 'error'},
               {'regex': 'POSSIBLE BREAK-IN ATTEMPT', 'level': 'warning'},
               {'regex': 'Network error:', 'level': 'error'},
               {'regex': 'Access denied', 'level': 'error'},
               {'regex': 'Authentication refused', 'level': 'error'},
               {'regex': 'Out of memory', 'level': 'error'},
               {'regex': 'Connection reset by peer', 'level': 'warning'},
               {'regex': 'Host key verification failed', 'level': 'error'},
               {'regex': 'command not found', 'level': 'error'},
               {'regex': 'WARNING:', 'level': 'warning'},
               {'regex': 'rsync error:', 'level': 'error'},
               {'regex': 'Broken pipe:', 'level': 'error'},
               {'regex': 'connection unexpectedly closed:', 'level': 'error'},
              ]

HgErrorRegex=[{'regex': '^abort:', 'level': 'error'},
              {'regex': 'command not found', 'level': 'error'},
              {'regex': 'unknown exception encountered', 'level': 'error'},
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

    def rmtree(self, path, errorLevel='error', exitCode=-1):
        self.info("rmtree: %s" % path)
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            if os.path.exists(path):
                self.log('Unable to remove %s!' % path, level=errorLevel,
                         exitCode=exitCode)
        else:
            self.debug("%s doesn't exist." % path)

    # http://www.techniqal.com/blog/2008/07/31/python-file-read-write-with-urllib2/
    def downloadFile(self, url, fileName=None, testOnly=False,
                     errorLevel='error', exitCode=-1):
        """Python wget.
        TODO: option to mkdir_p dirname(fileName) if it doesn't exist.
        """
        if not fileName:
            fileName = os.basename(url)
        if testOnly:
            self.info("Touching %s instead of downloading..." % fileName)
            os.system("touch %s" % fileName)
            return fileName
        req = urllib2.Request(url)
        try:
            self.info("Downloading %s" % url)
            f = urllib2.urlopen(req)
            localFile = open(fileName, 'w')
            localFile.write(f.read())
            localFile.close()
        except urllib2.HTTPError, e:
            self.log("HTTP Error: %s %s" % (e.code, url), level=errorLevel,
                     exitCode=exitCode)
            return
        except urllib2.URLError, e:
            self.log("URL Error: %s %s" % (e.code, url), level=errorLevel,
                       exitCode=exitCode)
            return
        return fileName

    def move(self, src, dest):
        self.info("Moving %s to %s" % (src, dest))
        shutil.move(src, dest)

    def runCommand(self, command, cwd=None, errorRegex=[], parseAtEnd=False,
                   shell=True):
        """Run a command, with logging and error parsing.

        TODO: parseAtEnd, contextLines
        TODO: retryInterval?
        TODO: errorLevelOverride?
        TODO: successCodes=[0] ?
        TODO: make it an either/or for 'regex' or 'match' for less time
              spent in re.search() (regex for real regexes, match for
              if match in line: ) ?

        errorRegex example:
        [{'regex': '^Error: LOL J/K', level='ignore'},
         {'regex': '^Error:', level='error', contextLines='5:5'},
         {'regex': 'THE WORLD IS ENDING', level='fatal', contextLines='20:'}
        ]
        """
        if cwd:
            if not os.path.isdir(cwd):
                self.error("Can't run command %s in non-existent directory %s!" % \
                           (command, cwd))
                return -1
            self.info("Running command: %s in %s" % (command, cwd))
        else:
            self.info("Running command: %s" % command)
        p = subprocess.Popen(command, shell=shell, stdout=subprocess.PIPE,
                             cwd=cwd, stderr=subprocess.STDOUT)
        stdout, stderr = p.communicate()
        lines = stdout.rstrip().split('\n') # \r detection?
        for line in lines:
            if not line or line.isspace():
                continue
            for errorCheck in errorRegex:
                if re.search(errorCheck['regex'], line):
                    self.log(' %s' % line,
                             level=errorCheck.get('level', 'info'))
                    break
            else:
                self.info(' %s' % line)
        returnLevel = 'info'
        if p.returncode != 0:
            returnLevel = 'error'
        self.log("Return code: %d" % p.returncode, level=returnLevel)
        return p.returncode                             



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

    def __init__(self, logLevel='info',
                 logFormat='%(message)s',
                 logDateFormat='%H:%M:%S',
                 logName='test',
                 logToConsole=True,
                 logDir='.',
                 logToRaw=False,
                 loggerName='',
                 haltOnFailure=True,
                 appendToLog=False,
                ):
        self.haltOnFailure = haltOnFailure,
        self.logFormat = logFormat
        self.logDateFormat = logDateFormat
        self.logToConsole = logToConsole
        self.logToRaw = logToRaw
        self.logLevel = logLevel
        self.logName = logName
        self.logDir = logDir
        self.appendToLog = appendToLog

        # Not sure what I'm going to use this for; useless unless we
        # can have multiple logging objects that don't trample each other
        self.loggerName = loggerName

        self.allHandlers = []
        self.logFiles = {}

        self.createLogDir()

    def createLogDir(self):
        if os.path.exists(self.logDir):
            if not os.path.isdir(self.logDir):
                os.remove(self.logDir)
        if not os.path.exists(self.logDir):
            os.makedirs(self.logDir)
        self.absLogDir = os.path.abspath(self.logDir)


    def getLoggerLevel(self, level=None):
        if not level:
            level = self.logLevel
        return self.LEVELS.get(level, logging.NOTSET)

    def getLogFormatter(self, logFormat=None, dateFormat=None):
        if not logFormat:
            logFormat = self.logFormat
        if not dateFormat:
            dateFormat = self.logDateFormat
        return logging.Formatter(logFormat, dateFormat)

    def newLogger(self, loggerName):
        """Create a new logger.
        By default there are no handlers.
        """
        self.logger = logging.getLogger(loggerName)
        self.logger.setLevel(self.getLoggerLevel())
        self._clearHandlers()
        if self.logToConsole:
            self.addConsoleHandler()
        if self.logToRaw:
            self.logFiles['raw'] = '%s_raw.log' % self.logName
            self.addFileHandler(os.path.join(self.absLogDir,
                                             self.logFiles['raw']),
                                logFormat='%(message)s')

    def _clearHandlers(self):
        """To prevent dups -- logging will preserve Handlers across
        objects :(
        """
        attrs = dir(self)
        if 'allHandlers' in attrs and 'logger' in attrs:
            for handler in self.allHandlers:
                self.logger.removeHandler(handler)
            self.allHandlers = []

    def __del__(self):
        self._clearHandlers()

    def addConsoleHandler(self, logLevel=None, logFormat=None,
                          dateFormat=None):
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(self.getLoggerLevel(logLevel))
        consoleHandler.setFormatter(self.getLogFormatter(logFormat=logFormat,
                                                         dateFormat=dateFormat))
        self.logger.addHandler(consoleHandler)
        self.allHandlers.append(consoleHandler)

    def addFileHandler(self, logPath, logLevel=None, logFormat=None,
                       dateFormat=None):
        if not self.appendToLog and os.path.exists(logPath):
            os.remove(logPath)
        fileHandler = logging.FileHandler(logPath)
        fileHandler.setLevel(self.getLoggerLevel(logLevel))
        fileHandler.setFormatter(self.getLogFormatter(logFormat=logFormat,
                                                      dateFormat=dateFormat))
        self.logger.addHandler(fileHandler)
        self.allHandlers.append(fileHandler)

    def log(self, message, level='info', exitCode=-1):
        """Generic log method.
        There should be more options here -- do or don't split by line,
        use os.linesep instead of assuming \n, be able to pass in log level
        by name or number.

        Adding the "ignore" special level for runCommand.
        """
        if level == "ignore":
            return
        for line in message.split('\n'):
            self.logger.log(self.getLoggerLevel(level), line)
        if level == 'fatal' and self.haltOnFailure:
            self.logger.log(FATAL, 'Exiting %d' % exitCode)
            sys.exit(exitCode)

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

    def fatal(self, message, exitCode=-1):
        self.log(message, level='fatal', exitCode=exitCode)



# SimpleFileLogger {{{1
class SimpleFileLogger(BaseLogger):
    """Create one logFile.  Possibly also output to
    the terminal and a raw log (no prepending of level or date)
    """
    def __init__(self,
                 logFormat='%(asctime)s - %(levelname)s - %(message)s',
                 loggerName='Simple', logDir='logs', **kwargs):
        BaseLogger.__init__(self, loggerName=loggerName, logFormat=logFormat,
                            logDir=logDir, **kwargs)
        self.newLogger(self.loggerName)
        self.info("SimpleFileLogger online at %s in %s" % \
                  (datetime.now().strftime("%Y %B %d %H:%M:%S"),
                   os.getcwd()))

    def newLogger(self, loggerName):
        BaseLogger.newLogger(self, loggerName)
        self.logPath = os.path.join(self.absLogDir, '%s.log' % self.logName)
        self.logFiles['default'] = self.logPath
        self.addFileHandler(self.logPath)




# MultiFileLogger {{{1
class MultiFileLogger(BaseLogger):
    """Create a log per log level in logDir.  Possibly also output to
    the terminal and a raw log (no prepending of level or date)
    """
    def __init__(self, loggerName='Multi',
                 logFormat='%(asctime)s - %(levelname)s - %(message)s',
                 logDir='logs', logToRaw=True, **kwargs):
        BaseLogger.__init__(self, loggerName=loggerName, logFormat=logFormat,
                            logToRaw=logToRaw, logDir=logDir,
                            **kwargs)

        self.newLogger(self.loggerName)
        self.info("MultiFileLogger online at %s in %s" % \
                  (datetime.now().strftime("%Y %B %d %H:%M:%S"),
                   os.getcwd()))

    def newLogger(self, loggerName):
        BaseLogger.newLogger(self, loggerName)
        minLoggerLevel = self.getLoggerLevel(self.logLevel)
        for level in self.LEVELS.keys():
            if self.getLoggerLevel(level) >= minLoggerLevel:
                self.logFiles[level] = '%s_%s.log' % (self.logName,
                                                      level)
                self.addFileHandler(os.path.join(self.absLogDir,
                                                 self.logFiles[level]),
                                    logLevel=level)



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

    logDir = 'test_logs'
    obj = MultiFileLogger(logLevel='info', logDir=logDir,
                          logToRaw=True)
    testLogger(obj)
    obj.haltOnFailure=False
    obj.log('test fatal -- you should *not* see an exit line after this.',
            level='fatal')
    obj = SimpleFileLogger(logDir=logDir)
    testLogger(obj)
    print "=========="
    print "You should be able to examine %s." % logDir
