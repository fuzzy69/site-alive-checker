# -*- coding: UTF-8 -*-
#!/usr/bin/env python

from time import sleep

from PyQt5.QtCore import QThread, pyqtSlot, pyqtSignal, QObject

from .utils import check_alive

class MyThread(QThread):
    activeCount = 0

    def __init__(self, parent=None):
        super(QThread, self).__init__()
        self.started.connect(self.increaseActiveThreads)
        self.finished.connect(self.decreaseActiveThreads)

    @pyqtSlot()
    def increaseActiveThreads(self):
        MyThread.activeCount += 1

    @pyqtSlot()
    def decreaseActiveThreads(self):
        MyThread.activeCount -= 1

class Worker(QObject):
    start = pyqtSignal()
    finished = pyqtSignal()
    result = pyqtSignal(object)

    def __init__(self, func, *args, **kwargs):
        super(Worker, self).__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.start.connect(self.run)
        self._running = False

    @pyqtSlot()
    def run(self):
        self._running = True
        result = self.doWork(*self._args, **self._kwargs)
        self.finished.emit()

    def doWork(self, *args, **kwargs):
        raise NotImplementedError

class CheckAliveWorker(Worker):
    status = pyqtSignal(tuple)

    def doWork(self, *args, **kwargs):
        queue = kwargs["queue"]
        timeout = kwargs["timeout"]
        while self._running and not queue.empty():
            row, url = queue.get()
            self.status.emit((row, "Checking ..."))
            status_code, msg = check_alive(url, timeout)
            result = True if status_code in [200, 301] else False
            self.result.emit({
                "row": row,
                "url": url,
                "result": result,
                "status_code": status_code,
            })
            self.status.emit((row, "Done"))

    def test(self):
        print("Ok")