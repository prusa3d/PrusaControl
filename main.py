#!/usr/bin/env python
# -*- coding: utf-8 -*-
import atexit
#import inspect
#from msilib.schema import File

from PyQt4.QtGui import QApplication, QIcon
from PyQt4 import QtGui
#from tendo.singleton import SingleInstance

from controller import Controller
from parameters import AppParameters
from sceneRender import *
#from sceneData import *
import logging
import cProfile
import os
import platform
#import shutil


__author__ = 'Tibor Vavra'

DEBUG = True

class EventLoopRunner(QObject):
    finished = pyqtSignal()

    def __init__(self, app, base_path=""):
        super(EventLoopRunner, self).__init__()
        self.base_path = base_path
        self.app = app
        self.version = ""

        with __builtins__.open(self.base_path + "data/v.txt", 'r') as version_file:
            self.version_full = version_file.read()
            self.version = AppParameters.strip_version_string(self.version_full)

        self.is_running = True
        self.css = []
        self.splash_pix = []
        self.splash = []
        self.progressBar = []

        self.initializeGUI()

    def initializeGUI(self):
        self.css = QFile(self.base_path + 'data/my_stylesheet.qss')
        self.css.open(QIODevice.ReadOnly)

        self.splash_pix = QPixmap(self.base_path + 'data/img/splashscreen.png')
        self.splash = QSplashScreen(self.splash_pix, Qt.SplashScreen | Qt.WindowStaysOnTopHint)

        self.progressBar = QProgressBar(self.splash)
        self.progressBar.setObjectName("splash_progressbar")
        self.progressBar.setFormat("")
        self.progressBar.setFixedWidth(209)
        self.progressBar.setFixedHeight(6)
        self.progressBar.move(245, 453)

        self.version_label = QLabel(self.version, self.splash)
        self.version_label.setObjectName("version_label")
        self.version_label.move(620, 647)

        self.splash.show()

        self.progressBar.setValue(0)

    def process_event_loop(self):
        while self.is_running == True:
            self.app.processEvents()



def log_exception(excType, excValue, traceback):
    logging.error("Logging an uncaught exception",
                 exc_info=(excType, excValue, traceback))

    sys.__excepthook__(excType, excValue, traceback)



def main():
    if getattr(sys, 'frozen', False):
        # it is freeze app
        base_dir = sys._MEIPASS
    else:
        # we are running in a normal Python environment
        base_dir = os.path.dirname(os.path.abspath(__file__))

    system_platform = platform.system()
    if system_platform in ['Windows']:
        base_dir+='\\'
    else:
        base_dir+='/'

    sys.excepthook = log_exception

    app = QApplication(sys.argv)
     
    app.setApplicationName("PrusaControl")
    app.setOrganizationName("Prusa Research")
    app.setOrganizationDomain("prusa3d.com")

    dpi = app.desktop().logicalDpiX()

    app.setWindowIcon(QIcon(base_dir + "data/icon/favicon.ico"))
    #print("Dpi je: " + str(dpi))
    if dpi == 96:
        file = QFile(base_dir + "data/my_stylesheet.qss")
    #elif dpi == 72:
    #    file = QFile(base_dir + "data/my_stylesheet.qss")
    else:
        file = QFile(base_dir + "data/my_stylesheet_without_f.qss")
    file.open(QFile.ReadOnly)
    
    StyleSheet_tmp = str(file.readAll(), 'utf-8')
    if system_platform in ['Windows']:
        StyleSheet = StyleSheet_tmp.replace('base_dir', "")
    else:
        StyleSheet = StyleSheet_tmp.replace('base_dir', base_dir)

    app.setStyle(QStyleFactory.create("windows"))
    app.setStyleSheet(StyleSheet)
   
    

    event_loop_runner = EventLoopRunner(app, base_dir)
    event_loop_runner_thread = QThread()
    event_loop_runner.moveToThread(event_loop_runner_thread)
    event_loop_runner_thread.started.connect(event_loop_runner.process_event_loop)

    progressBar = event_loop_runner.progressBar

    event_loop_runner_thread.start()

    #local_path = os.path.realpath(__file__)

    controller = Controller(app, base_dir, progressBar)
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
    system_platform = platform.system()
    log_path = "/"
    if system_platform in ['Windows']:
        log_path = "\\"
    else:
        log_path = "/"
    FORMAT = "[%(levelname)s][%(filename)s:%(lineno)s:%(funcName)s()]-%(message)s"

    if DEBUG:
        logging.basicConfig(filename=os.path.expanduser("~" + log_path + "prusacontrol.log"), format=FORMAT, filemode='w', level=logging.DEBUG)
        #cProfile.runctx('main()', globals(), locals(), 'prusacontrol.profile')
    else:
        logging.basicConfig(filename=os.path.expanduser("~" + log_path + "prusacontrol.log"), format=FORMAT, filemode='w', level=logging.WARNING)
    
    main()
