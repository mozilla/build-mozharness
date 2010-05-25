#!/usr/bin/env python

import logging
import os
import sys

# Define our own FATAL
FATAL = logging.CRITICAL + 10
logging.addLevelName(FATAL, 'FATAL')

class BaseLogger(object):
    LEVELS = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'warn': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL,
              'fatal': logging.FATAL
             }

    def __init__(self,
                 objName='Base',
                 haltOnFailure=True,
                 logDateFormat='%H:%M:%S',
                 logFormat='%(asctime)s - %(levelname)s - %(message)s',
                 logLevel='info',
                 logName='default.log',
                 logToConsole=True,
                 logToFile=False,
                ):
        self.objName = objName
        self.haltOnFailure = haltOnFailure,
        self.logLevel = logLevel
        self.logDateFormat = logDateFormat
        self.logFormat = logFormat
        self.logName = logName
        self.logToConsole = logToConsole
        self.logToFile = logToFile
        self.allHandlers = []

        self.newLogger(self.objName)

    def initMessage(self):
        """Optionally log an initial message.
        """
        pass

    def newLogger(self, loggerName):
        """Create a new logger.
        """
        self.realLogLevel = self.LEVELS.get(self.logLevel, logging.NOTSET)

        self.logger = logging.getLogger(loggerName)
        self.logger.setLevel(self.realLogLevel)
        self.logFormatter = logging.Formatter(self.logFormat,
                                              self.logDateFormat)

        # To prevent dups if called multiple times
        for handler in self.allHandlers:
            self.logger.removeHandler(handler)

        if self.logToConsole:
            self.addConsoleHandler()
        if self.logToFile:
            self.addFileHandler(self.logName)
        self.initMessage()

    def addConsoleHandler(self):
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(self.realLogLevel)
        consoleHandler.setFormatter(self.logFormatter)
        self.logger.addHandler(consoleHandler)
        self.allHandlers.append(consoleHandler)

    def addFileHandler(self, logName):
        fileHandler = logging.FileHandler(logName)
        fileHandler.setLevel(self.realLogLevel)
        fileHandler.setFormatter(self.logFormatter)
        self.logger.addHandler(fileHandler)
        self.allHandlers.append(fileHandler)

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



if __name__ == '__main__':
    testLogName = 'test.log'
    if os.path.exists(testLogName):
        os.remove(testLogName)
    obj = BaseLogger(logLevel='debug', logName=testLogName, logToFile=True)
    obj.debug('test debug')
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
    if os.path.exists(testLogName):
        os.remove(testLogName)
    else:
        print "CAN'T REMOVE %s!" % testLogName

    # Test after resetting the logger
    obj.logLevel='critical'
    obj.haltOnFailure=False
    obj.logToFile=False
    obj.newLogger('Base')
    obj.error('YOU SHOULD NOT SEE THIS MESSAGE!')
    obj.critical('test critical -- You should see this message.')
    obj.fatal('test fatal -- you should *not* see an exit line after this.')
