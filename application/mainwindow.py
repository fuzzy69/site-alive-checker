# -*- coding: UTF-8 -*-
# !/usr/bin/env python

import os
import webbrowser
from queue import Queue

from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import (Qt, QSettings, QThread, QTimer, pyqtSlot, pyqtSignal)
from PyQt5.QtGui import (QFont, QStandardItem, QStandardItemModel)

from .conf import ROOT
from .defaults import THREADS, TIMEOUT
from .helpers import readTextFile
from .utils import check_alive, split_list
from .version import __version__
from .workers import Worker, CheckAliveWorker

ui = uic.loadUiType(os.path.join(ROOT, "assets", "ui", "mainwindow.ui"))[0]

class MainWindow(QtWidgets.QMainWindow, ui):
    def __init__(self, parent=None, title=""):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.setWindowTitle("{} {}".format(title, __version__))
        self._settingsFile = os.path.join(ROOT, "data", "settings.ini")
        self._threadPool = []
        self.sitesModel = QStandardItemModel()
        self.sitesModel.setHorizontalHeaderLabels(["URL", "Result", "Code", "Status"])
        self.sitesTableView.setModel(self.sitesModel)
        # Menubar
        self.importUrlsAction_2.triggered.connect(self.importUrls)
        self.exportResultsAction.triggered.connect(self.exportResults)
        self.quitAction.triggered.connect(lambda: QtWidgets.QApplication.quit())
        self.clearTableAction_2.triggered.connect(self.clearTable)
        self.aboutAction.triggered.connect(self.about)
        # Toolbar
        self.importUrlsAction.triggered.connect(self.importUrls)
        self.clearTableAction.triggered.connect(self.clearTable)
        # Widgets
        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.sitesTableView.doubleClicked.connect(self.sitesTableView_doubleClicked)
        # Events
        self.resizeEvent = self.onResize
        self.closeEvent = self.onClose
        self.showEvent = self.onShow
        self._tableViewWidth = 0
        self._threads = []
        self._workers = []
        self._progressDone = 0
        self._progressTotal = 0
        self._boldFont = QFont()
        self._boldFont.setBold(True)
        self.loadSettings()
        self.centerWindow()

    def centerWindow(self):
        fg = self.frameGeometry()
        c = QtWidgets.QDesktopWidget().availableGeometry().center()
        fg.moveCenter(c)
        self.move(fg.topLeft())

    def loadSettings(self):
        if os.path.isfile(self._settingsFile):
            settings = QSettings(self._settingsFile, QSettings.IniFormat)
            self.restoreGeometry(settings.value("geometry", ''))
            self.restoreState(settings.value("windowState", ''))
            self._tableViewWidth = int(settings.value("tableViewWidth", ''))
            self.threadsSpin.setValue(settings.value("threadsCount", THREADS, type=int))
            self.timeoutSpin.setValue(settings.value("timeoutSpin", TIMEOUT, type=int))

    def saveSettings(self):
        settings = QSettings(self._settingsFile, QSettings.IniFormat)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("tableViewWidth", self.sitesTableView.frameGeometry().width())
        settings.setValue("threadsCount", self.threadsSpin.value())
        settings.setValue("timeout", self.timeoutSpin.value())

    def onResize(self, event):
        self.resizeTableColumns()
        QtWidgets.QMainWindow.resizeEvent(self, event)

    def onClose(self, event):
        self.saveSettings()
        QtWidgets.QMainWindow.closeEvent(self, event)

    def onShow(self, event):
        self.resizeTableColumns()
        QtWidgets.QMainWindow.showEvent(self, event)

    def resizeTableColumns(self):
        self.sitesTableView.setColumnWidth(0, int(self.sitesTableView.frameGeometry().width() * 0.6))
        self.sitesTableView.setColumnWidth(1, int(self.sitesTableView.frameGeometry().width() * 0.1))

    def start(self):
        model = self.sitesModel
        queues = split_list(range(self.sitesModel.rowCount()), self.threadsSpin.value())
        self._progressTotal = self.sitesModel.rowCount()
        for i, rows in enumerate(queues):
            self._threads.append(QThread())
            queue = Queue()
            for row in rows:
                url = model.data(model.index(row, 0))
                queue.put((row, url))
            self._workers.append(CheckAliveWorker(check_alive, timeout=self.timeoutSpin.value(), queue=queue))
            self._workers[i].moveToThread(self._threads[i])
            self._threads[i].started.connect(self._workers[i].start)
            self._threads[i].finished.connect(self._threads[i].deleteLater)
            self._workers[i].status.connect(self.onStatus)
            self._workers[i].result.connect(self.onResult)
            self._workers[i].finished.connect(self._threads[i].quit)
            self._workers[i].finished.connect(self._workers[i].deleteLater)
        for i in range(self.threadsSpin.value()):
            self._threads[i].start()

    def stop(self):
        for i, _ in enumerate(self._workers):
            self._workers[i]._running = False

    @pyqtSlot(tuple)
    def onStatus(self, tuple_):
        i, status = tuple_
        self.sitesModel.setData(self.sitesModel.index(i, 3), status)

    @pyqtSlot(object)
    def onResult(self, result):
        self.sitesModel.item(result["row"], 1).setFont(self._boldFont)
        self.sitesModel.item(result["row"], 1).setForeground(Qt.white)
        self.sitesModel.setData(self.sitesModel.index(result["row"], 2), result["status_code"])
        if result["result"]:
            self.sitesModel.setData(self.sitesModel.index(result["row"], 1), "OK")
            self.sitesModel.item(result["row"], 1).setBackground(Qt.green)
        else:
            self.sitesModel.setData(self.sitesModel.index(result["row"], 1), "Fail")
            self.sitesModel.item(result["row"], 1).setBackground(Qt.red)
        self._progressDone += 1
        self.progressBar.setValue(int(float(self._progressDone) / self._progressTotal * 100))

    def importUrls(self):
        filePath, fileType = QtWidgets.QFileDialog.getOpenFileName(self, "Import URLs", filter="Text files (*.txt)")
        if filePath:
            text = readTextFile(filePath)
            for url in text.strip().splitlines():
                self.sitesModel.appendRow([QStandardItem(url), QStandardItem(""),QStandardItem("")])

    def sitesTableView_doubleClicked(self, modelIndex):
        model = self.sitesModel
        row = modelIndex.row()
        url = model.data(model.index(row, 0))
        webbrowser.open(url)

    def clearTable(self):
        self.tableRemoveAllRows(self.sitesModel)

    def tableRemoveAllRows(self, model):
        for i in reversed(range(model.rowCount())):
            model.removeRow(i)

    def exportResults(self):
        pass

    def about(self):
        pass