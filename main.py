#!/usr/bin/env python
# -*- coding: utf-8 -*-
import atexit
from PyQt4 import QtGui

from controller import Controller
from sceneRender import *
from sceneData import *
import logging
import cProfile
import os


__author__ = 'Tibor Vavra'

DEBUG = False


def main():
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("data/icon/favicon.ico"))
    local_path = os.path.realpath(__file__)
    print("Local_path: " + local_path)

    controller = Controller(app, local_path)
    window = controller.get_view()
    #app.installEventFilter(window)
    app.exec_()
    atexit.register(controller.write_config)



if __name__ == '__main__':
    FORMAT = "[%(levelname)s][%(filename)s:%(lineno)s:%(funcName)s()]-%(message)s"
    logging.basicConfig(filename='prusacontrol.log', format=FORMAT, filemode='w', level=logging.INFO)

    if DEBUG:
        cProfile.runctx('main()', globals(), locals(), 'prusacontrol.profile')
    else:
        main()
