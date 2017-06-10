# -*- coding: UTF-8 -*-
#!/usr/bin/env python

import logging

from PyQt5.QtCore import QFile, QTextStream, QIODevice


class Logger(object):
    def __init__(self, name, level=logging.DEBUG, filename=None):
        self.instance = logging.getLogger(name)
        self.instance.setLevel(level)
        self.set_console_handler()
        if filename:
            self.set_file_handler(filename)

    def set_console_handler(self, level=logging.INFO):
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s %(message)s',
            '%H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.instance.addHandler(handler)

    def set_file_handler(self, filename, level=logging.DEBUG):
        handler = logging.FileHandler(filename)
        handler.setLevel(level)
        formatter = logging.Formatter(
            '[%(asctime)s] %(name)-12s: %(levelname)-8s %(message)s',
            '%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.instance.addHandler(handler)

    def info(self, message):
        self.instance.info(message)

    def debug(self, message):
        self.instance.debug(message)

    def warning(self, message):
        self.instance.warning(message)

    def error(self, message):
        self.instance.error(message)

    def log(self, level, message):
        if level == "info":
            self.info(message)
        elif level == "debug":
            self.debug(message)
        elif level == "warning":
            self.warning(message)
        elif level == "error":
            self.error(message)

def readTextFile(filePath):
    f = QFile(filePath)
    if not f.open(QIODevice.ReadOnly):
        return False
    ts = QTextStream(f)

    return ts.readAll()

def writeTextFile(filePath, fileContents):
    pass