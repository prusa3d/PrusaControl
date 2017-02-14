#!/usr/bin/env python
# -*- coding: utf-8 -*-
import atexit

from PyQt4.QtGui import QApplication, QIcon
#from tendo.singleton import SingleInstance
from PyQt4 import QtGui

from controller import Controller
from sceneRender import *
#from sceneData import *
import logging
import cProfile
import os
#import shutil


__author__ = 'Tibor Vavra'

DEBUG = False

def log_exception(excType, excValue, traceback):
    logging.error("Logging an uncaught exception",
                 exc_info=(excType, excValue, traceback))

    sys.__excepthook__(excType, excValue, traceback)

def main():
    sys.excepthook = log_exception


    try:
        if sys.frozen or sys.importers:
            SCRIPT_ROOT = os.path.dirname(sys.executable)
    except AttributeError:
        SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))

    #me = SingleInstance()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("data/icon/favicon.ico"))

    css = QFile('data/my_stylesheet.css')
    css.open(QIODevice.ReadOnly)


    splash_pix = QPixmap('data/img/splashscreen.png')
    splash = QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    progressBar = QProgressBar(splash)
    progressBar.setFixedWidth(splash.width())

    if css.isOpen():
        progressBar.setStyleSheet(QVariant(css.readAll()).toString())
        css.close()

    splash.setMask(splash_pix.mask())
    splash.show()

    progressBar.setValue(0)

    '''
    for i in range(0, 100):
        progressBar.setValue(i)
        t = time.time()
        while time.time() < t + 0.1:
            app.processEvents()
    '''


    local_path = os.path.realpath(__file__)

    controller = Controller(app, local_path, progressBar)
    progressBar.setValue(100)
    window = controller.get_view()
    splash.finish(window)
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
