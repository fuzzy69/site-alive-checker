# -*- coding: UTF-8 -*-
# !/usr/bin/env python

import os
import sys

from PyQt5 import uic, QtWidgets

from application.mainwindow import MainWindow

__author__ = "fuzzy69"
__title__ = "Site Alive Checker"

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet("QStatusBar::item { border: 0px solid black }; ");
    mainWindow = MainWindow(title=__title__)
    mainWindow.show()
    app.exec_()