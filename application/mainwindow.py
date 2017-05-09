# -*- coding: UTF-8 -*-
# !/usr/bin/env python

import csv
import json
import os
import platform
import webbrowser
from queue import Queue

from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import (Qt, QSettings, QThread, QTimer, pyqtSlot, pyqtSignal,
    QT_VERSION_STR, PYQT_VERSION_STR, QItemSelectionModel)
from PyQt5.QtGui import (QFont, QStandardItem, QStandardItemModel)

from .conf import ROOT, __author__, __description__, __title__
from .defaults import THREADS, TIMEOUT
from .helpers import readTextFile
from .utils import check_alive, split_list
from .version import __version__
from .workers import Worker, CheckAliveWorker, MyThread

ui = uic.loadUiType(os.path.join(ROOT, "assets", "ui", "mainwindow.ui"))[0]

class MainWindow(QtWidgets.QMainWindow, ui):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.setWindowTitle("{} - {}".format(__title__, __version__))
        self._settingsFile = os.path.join(ROOT, "data", "settings.ini")
        self._threadPool = []
        self.sitesModel = QStandardItemModel()
        self.sitesModel.setHorizontalHeaderLabels(["URL", "Result", "Code", "Status"])
        self.sitesTableView.setModel(self.sitesModel)
        self.importUrlsAction.triggered.connect(self.importUrls)
        self.exportResultsAction.triggered.connect(self.exportResults)
        self.quitAction.triggered.connect(lambda: QtWidgets.QApplication.quit())
        self.clearTableAction.triggered.connect(self.clearTable)
        self.aboutAction.triggered.connect(self.about)
        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.buttonTest.clicked.connect(self.test)
        self.sitesTableView.doubleClicked.connect(self.sitesTableView_doubleClicked)
        self.labelActiveThreads = QtWidgets.QLabel("Active threads: 0")
        self.statusbar.addPermanentWidget(self.labelActiveThreads)

        self.actionRemove_selected.triggered.connect(self.removeSelected)
        self.actionInvert_selection.triggered.connect(self.invertSelection)
        self.actionRemove_duplicates.triggered.connect(self.removeDuplicates)
        self.actionSelect_all.triggered.connect(self.sitesTableView.selectAll)

        # Events
        self.resizeEvent = self.onResize
        self.closeEvent = self.onClose
        self.showEvent = self.onShow
        self._tableViewWidth = 0
        self._threads = []
        self._activeThreads = 0
        self._workers = []
        self._progressDone = 0
        self._progressTotal = 0
        self._boldFont = QFont()
        self._boldFont.setBold(True)
        self._recentFIles = []
        self.loadSettings()
        self.centerWindow()
        self.timerPulse = QTimer(self)
        self.timerPulse.timeout.connect(self.pulse)
        self.timerPulse.start(1000)
        # text = readTextFile("data/sites2.txt")
        # for url in text.strip().splitlines():
        #     resultCell = QStandardItem("")
        #     # resultCell.setTextAlignment(Qt.AlignCeter)
        #     codeCell = QStandardItem("")
        #     # codeCell.setTextAlignment(Qt.AlignCenter)
        #     self.sitesModel.appendRow([QStandardItem(url), resultCell, codeCell])
        self.stopButton.setEnabled(False)
        self.buttonTest.setVisible(False)

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
        self.resetTable()
        model = self.sitesModel
        queues = split_list(range(self.sitesModel.rowCount()), self.threadsSpin.value())
        self._progressTotal = self.sitesModel.rowCount()
        self._progressDone = 0
        self._threads = []
        self._workers = []
        for i, rows in enumerate(queues):
            self._threads.append(MyThread())
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
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)

    def setActiveThreadsCount(self, i):
        self._activeThreads = i

    def pulse(self):
        # print("threads: " +str(MyThread.activeCount))
        self.labelActiveThreads.setText("Active threads: {}".format(MyThread.activeCount))
        if MyThread.activeCount == 0:
            if not self.sitesTableView.isSortingEnabled():
                self.sitesTableView.setSortingEnabled(True)
            if not self.startButton.isEnabled():
                self.startButton.setEnabled(True)
            if self.stopButton.isEnabled():
                self.stopButton.setEnabled(False)
        else:
            if self.sitesTableView.isSortingEnabled():
                self.sitesTableView.setSortingEnabled(False)

    def stop(self):
        for i, _ in enumerate(self._workers):
            self._workers[i]._running = False

    @pyqtSlot(tuple)
    def onStatus(self, tuple_):
        i, status = tuple_
        self.sitesModel.setData(self.sitesModel.index(i, 3), status)

    @pyqtSlot(object)
    def onResult(self, result):
        print(result)
        self.sitesModel.item(result["row"], 1).setFont(self._boldFont)
        # self.sitesModel.item(result["row"], 1).setForeground(Qt.white)
        self.sitesModel.setData(self.sitesModel.index(result["row"], 2), result["status_code"])
        if result["result"]:
            self.sitesModel.setData(self.sitesModel.index(result["row"], 1), "OK")
            self.sitesModel.item(result["row"], 1).setForeground(Qt.green)
        else:
            self.sitesModel.setData(self.sitesModel.index(result["row"], 1), "Fail")
            self.sitesModel.item(result["row"], 1).setForeground(Qt.red)
        self._progressDone += 1
        self.progressBar.setValue(int(float(self._progressDone) / self._progressTotal * 100))

    def importUrls(self):
        filePath, fileType = QtWidgets.QFileDialog.getOpenFileName(self, "Import URLs", filter="Text files (*.txt)")
        if filePath:
            text = readTextFile(filePath)
            for url in text.strip().splitlines():
                resultCell = QStandardItem("")
                resultCell.setTextAlignment(Qt.AlignCenter)
                codeCell = QStandardItem("")
                codeCell.setTextAlignment(Qt.AlignCenter)
                self.sitesModel.appendRow([QStandardItem(url), resultCell, codeCell])

    def sitesTableView_doubleClicked(self, modelIndex):
        model = self.sitesModel
        row = modelIndex.row()
        url = model.data(model.index(row, 0))
        webbrowser.open(url)

    def resetTable(self):
        model = self.sitesModel
        for i in range(model.rowCount()):
            model.setData(model.index(i, 1), "")
            model.setData(model.index(i, 2), "")

    def clearTable(self):
        self.tableRemoveAllRows(self.sitesModel)

    def tableRemoveAllRows(self, model):
        for i in reversed(range(model.rowCount())):
            model.removeRow(i)

    def exportResults(self):
        filePath, fileType = QtWidgets.QFileDialog.getSaveFileName(self, "Export URLs", filter="Text file (*.txt);;CSV file (*.csv);;JSON file (*.json)")
        model = self.sitesModel
        data = []
        for i in range(model.rowCount()):
            data.append({
                "URL": model.data(model.index(i, 0)),
                "Result": model.data(model.index(i, 1)),
                "Code": model.data(model.index(i, 2)),
            })
        if "*.txt" in fileType:
            with open(filePath, "w") as f:
                f.write("\n".join([i["URL"] for i in data]))
        elif "*.csv" in fileType:
            with open(filePath, "w") as f:
                w = csv.DictWriter(f, data[0].keys())
                w.writeheader()
                w.writerows(data)
        elif "*.json" in fileType:
            with open(filePath, "w") as f:
                f.write(json.dumps(data))

    def about(self):
        QtWidgets.QMessageBox.about(self, "About {}".format(__title__),
            """<b>{} v{}</b>
            <p>&copy; 2017.
            <p>{}
            <p>Python {} - Qt {} - PyQt {} on {}""".format(
                __title__, __version__, __description__,
                platform.python_version(), QT_VERSION_STR, PYQT_VERSION_STR,
                platform.system())
        )

    def test(self):
        pass

    def selectedRows(self):
        rows = set()
        for index in self.sitesTableView.selectionModel().selectedIndexes():
            rows.add(index.row())

        return list(rows)

    def removeSelected(self):
        model = self.sitesModel
        for i in reversed(self.selectedRows()):
            model.removeRow(i)

    def removeDuplicates(self):
        items = []
        foundDuplicates = False
        for i in range(self.sitesModel.rowCount()):
            item = self.sitesModel.data(self.sitesModel.index(i, 0))
            if item not in items:
                items.append(item)
            else:
                foundDuplicates = True
        print(items)
        if foundDuplicates:
            self.clearTable()
            for i, item in enumerate(items):
                self.sitesModel.setData(self.sitesModel.index(i, 0), item)

    def invertSelection(self):
        # self.sitesTableView.selectAll()
        selectedRows = self.selectedRows()
        self.sitesTableView.clearSelection()
        for i in range(self.sitesModel.rowCount()):
            if i not in selectedRows:
                self.sitesTableView.selectRow(i)
        # for index in self.sitesTableView.selectionModel():
        #     index.select()
        #     break
        # self.sitesTableView.selectionModel().select(self.sitesModel.index(0, 1), QItemSelectionModel.Deselect)