#!/usr/bin/env python
# -*- coding: utf-8 -*-
import atexit

from PyQt4 import QtGui
from tendo.singleton import SingleInstance

from controller import Controller
from sceneRender import *
from sceneData import *
import logging
import cProfile
import os
import shutil


__author__ = 'Tibor Vavra'

DEBUG = False

def log_exception(excType, excValue, traceback):
    #print("Loguji")
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

    me = SingleInstance()


    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("data/icon/favicon.ico"))

    local_path = os.path.realpath(__file__)

    controller = Controller(app, local_path)
    window = controller.get_view()
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
