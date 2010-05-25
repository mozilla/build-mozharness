#!/usr/bin/env python
"""Logging, the way I remember it from scripts gone by.
"""

import logging
import os
import sys

# Define our own FATAL
FATAL = logging.CRITICAL + 10
logging.addLevelName(FATAL, 'FATAL')



# BaseLogger {{{1
class BaseLogger(object):
    """Create a base logging class.
    """
    LEVELS = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL,
              'fatal': logging.FATAL
             }

    def __init__(self, defaultLogLevel='info',
                 defaultLogFormat='%(message)s',
                 defaultLogDateFormat='%H:%M:%S',
                 haltOnFailure=True,
                ):
        self.haltOnFailure = haltOnFailure,
        self.defaultLogLevel = defaultLogLevel
        self.defaultLogFormat = defaultLogFormat
        self.defaultLogDateFormat = defaultLogDateFormat
        self.allHandlers = []

    def getLoggerLevel(self, level=None):
        if not level:
            level = self.defaultLogLevel
        return self.LEVELS.get(level, logging.NOTSET)

    def getFormatter(self, logFormat=None, dateFormat=None):
        if not logFormat:
            logFormat = self.defaultLogFormat
        if not dateFormat:
            dateFormat = self.defaultLogDateFormat
        return logging.Formatter(logFormat, dateFormat)

    def newLogger(self, loggerName):
        """Create a new logger.
        """
        self.logger = logging.getLogger(loggerName)
        self.logger.setLevel(self.getLoggerLevel())

        # To prevent dups if called multiple times
        for handler in self.allHandlers:
            self.logger.removeHandler(handler)

    def addConsoleHandler(self, logLevel=None, logFormat=None,
                          dateFormat=None):
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(self.getLoggerLevel(logLevel))
        consoleHandler.setFormatter(self.getFormatter(logFormat=logFormat,
                                                      dateFormat=dateFormat))
        self.logger.addHandler(consoleHandler)
        self.allHandlers.append(consoleHandler)

    def addFileHandler(self, logName, logLevel=None, logFormat=None,
                       dateFormat=None):
        fileHandler = logging.FileHandler(logName)
        fileHandler.setLevel(self.getLoggerLevel(logLevel))
        fileHandler.setFormatter(self.getFormatter(logFormat=logFormat,
                                                   dateFormat=dateFormat))
        self.logger.addHandler(fileHandler)
        self.allHandlers.append(fileHandler)

    def log(self, level, message):
        if level == 'fatal':
            self.fatal(message)
        else:
            self.logger.log(self.getLoggerLevel(level), message)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def warn(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

    def fatal(self, message, exitCode=-1):
        self.logger.log(FATAL, message)
        if self.haltOnFailure:
            self.logger.log(FATAL, 'Exiting %d' % exitCode)
            sys.exit(exitCode)



# MultiFileLogger {{{1
class MultiFileLogger(BaseLogger):
    """Create a log per log level in logDir.  Possibly also output to
    the terminal and a raw log (no prepending of level or date)
    """
    def __init__(self, baseLogName='test',
                 defaultLogFormat='%(asctime)s - %(levelname)s - %(message)s',
                 loggerName='', logDir='logs', logToConsole=True,
                 logToRaw=True, **kwargs):
        self.baseLogName = baseLogName
        self.logDir = logDir
        self.loggerName = loggerName
        self.logToConsole = logToConsole
        self.logToRaw = logToRaw
        self.logFiles = {}
        BaseLogger.__init__(self, defaultLogFormat=defaultLogFormat,
                            **kwargs)

        self.createLogDir()
        self.newLogger(self.loggerName)

    def createLogDir(self):
        if os.path.exists(self.logDir):
            if not os.path.isdir(self.logDir):
                os.remove(self.logDir)
        if not os.path.exists(self.logDir):
            os.makedirs(self.logDir)
        self.absLogDir = os.path.abspath(self.logDir)

    def newLogger(self, loggerName):
        BaseLogger.newLogger(self, loggerName)
        if self.logToConsole:
            self.addConsoleHandler()
        if self.logToRaw:
            self.logFiles['raw'] = '%s_raw.log' % self.baseLogName
            self.addFileHandler('%s/%s' % (self.absLogDir,
                                           self.logFiles['raw']),
                                logFormat='%(message)s')
        minLoggerLevel = self.getLoggerLevel(self.defaultLogLevel)
        for level in self.LEVELS.keys():
            if self.getLoggerLevel(level) >= minLoggerLevel:
                self.logFiles[level] = '%s_%s.log' % (self.baseLogName,
                                                      level)
                self.addFileHandler('%s/%s' % (self.absLogDir,
                                               self.logFiles[level]),
                                    logLevel=level)



# __main__ {{{1
if __name__ == '__main__':
    """Quick 'n' dirty unit tests.
    Ideally, this would be parsed automatically, too, and wouldn't leave
    cruft behind.
    """
    logDir = 'test_logs'
    obj = MultiFileLogger(defaultLogLevel='info', logDir=logDir,
                          logToRaw=True)
    obj.debug('YOU SHOULD NOT SEE THIS LINE')
    obj.info('test info')
    obj.warn('test warn')
    obj.error('test error')
    obj.critical('test critical')
    try:
        obj.fatal('test fatal -- you should see an exit line after this.')
    except:
        print "Yay, that's good."
    else:
        print "OH NO!"
    obj.haltOnFailure=False
    obj.critical('test critical -- You should see this message.')
    obj.fatal('test fatal -- you should *not* see an exit line after this.')
    print "=========="
    print "You should be able to examine the test logs created in %s." % logDir
