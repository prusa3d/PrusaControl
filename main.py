#!/usr/bin/env python
# -*- coding: utf-8 -*-
import atexit
from PyQt4 import QtGui

from controller import Controller
from sceneRender import *
from sceneData import *
import logging
import profile


__author__ = 'Tibor Vavra'

DEBUG = False

def main():
    logging.info('PrusaControl start')
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("data/icon/favicon.ico"))
    controller = Controller(app)
    window = controller.get_view()
    app.installEventFilter(window)
    app.exec_()
    logging.info('PrusaControl exit')
    atexit.register(controller.write_config)



if __name__ == '__main__':
    FORMAT = "[%(levelname)s][%(filename)s:%(lineno)s:%(funcName)s()]-%(message)s"
    logging.basicConfig(format=FORMAT, filemode='w', level=logging.INFO)

    if DEBUG:
        profile.run('main()')
    else:
        main()
