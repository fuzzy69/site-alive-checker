# -*- coding: UTF-8 -*-
# !/usr/bin/env python

import os
import sys

from PyQt5 import uic, QtWidgets

from application.conf import __title__
from application.mainwindow import MainWindow


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet("QStatusBar::item { border: 0px solid black }; ");
    mainWindow = MainWindow()
    mainWindow.show()
    app.exec_()