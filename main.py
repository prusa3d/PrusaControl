#!/usr/bin/env python
# -*- coding: utf-8 -*-
import atexit
import inspect
from msilib.schema import File

from PyQt4.QtGui import QApplication, QIcon
from PyQt4 import QtGui
#from tendo.singleton import SingleInstance

from controller import Controller
from sceneRender import *
#from sceneData import *
import logging
import cProfile
import os
#import shutil


__author__ = 'Tibor Vavra'

DEBUG = False

class EventLoopRunner(QObject):
    finished = pyqtSignal()

    def __init__(self, app):
        super(EventLoopRunner, self).__init__()
        self.app = app

        self.is_running = True
        self.css = []
        self.splash_pix = []
        self.splash = []
        self.progressBar = []

        self.initializeGUI()

    def initializeGUI(self):
        self.css = QFile('data/my_stylesheet.css')
        self.css.open(QIODevice.ReadOnly)

        self.splash_pix = QPixmap('data/img/splashscreen.png')
        self.splash = QSplashScreen(self.splash_pix, Qt.SplashScreen | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.WA_TranslucentBackground)
        self.progressBar = QProgressBar(self.splash)
        self.progressBar.setObjectName("splash_progressbar")
        self.progressBar.setFormat("")
        self.progressBar.setFixedWidth(209)
        self.progressBar.setFixedHeight(6)
        self.progressBar.move(208, 367)

        #if self.css.isOpen():
        #    self.progressBar.setStyleSheet(QVariant(self.css.readAll()).toString())
        #    self.css.close()

        self.splash.setMask(self.splash_pix.mask())
        self.splash.show()

        self.progressBar.setValue(0)

    def process_event_loop(self):
        while self.is_running == True:
            self.app.processEvents()

        #self.finished.emit()
        #print("Konec event smycky")


def log_exception(excType, excValue, traceback):
    logging.error("Logging an uncaught exception",
                 exc_info=(excType, excValue, traceback))

    sys.__excepthook__(excType, excValue, traceback)

def main():
    sys.excepthook = log_exception

    #vers = ['%s = %s' % (k, v) for k, v in vars(Qt).items() if k.lower().find('version') >= 0 and not inspect.isbuiltin(v)]
    #print('\n'.join(sorted(vers)))

    #try:
    #    if sys.frozen or sys.importers:
    #        SCRIPT_ROOT = os.path.dirname(sys.executable)
    #except AttributeError:
    #    SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))

    #me = SingleInstance()
    #QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    #QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    dpi = app.desktop().logicalDpiX()
    print(dpi)

    app.setWindowIcon(QIcon("data/icon/favicon.ico"))
    if dpi==96:
        file = QFile("data/my_stylesheet.qss")
    else:
        file = QFile("data/my_stylesheet_without_f.qss")
    file.open(QFile.ReadOnly)
    StyleSheet = str(file.readAll(), 'utf-8')
    app.setStyleSheet(StyleSheet)


    event_loop_runner = EventLoopRunner(app)
    event_loop_runner_thread = QThread()
    event_loop_runner.moveToThread(event_loop_runner_thread)
    event_loop_runner_thread.started.connect(event_loop_runner.process_event_loop)

    #event_loop_runner.finished.connect(set_finished_read)
    progressBar = event_loop_runner.progressBar

    event_loop_runner_thread.start()

    local_path = os.path.realpath(__file__)

    controller = Controller(app, local_path, progressBar)
    progressBar.setValue(100)
    window = controller.get_view()

    event_loop_runner.is_running = False
    event_loop_runner_thread.quit()
    event_loop_runner_thread.wait()
    event_loop_runner.splash.finish(window)

    controller.check_version()
    app.installEventFilter(window)
    app.exec_()
    atexit.register(controller.write_config)



if __name__ == '__main__':
    FORMAT = "[%(levelname)s][%(filename)s:%(lineno)s:%(funcName)s()]-%(message)s"
    #logging.basicConfig(filename='prusacontrol.log', format=FORMAT, filemode='w', level=logging.DEBUG)
    logging.basicConfig(filename=os.path.expanduser("~\\prusacontrol.log"), format=FORMAT, filemode='w', level=logging.DEBUG)

    if DEBUG:
        cProfile.runctx('main()', globals(), locals(), 'prusacontrol.profile')
    else:
        main()
