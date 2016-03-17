#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import Controller
from sceneRender import *
from sceneData import *
import logging

__author__ = 'Tibor Vavra'

if __name__ == '__main__':
    logging.basicConfig(filename='info.log', filemode='r', level=logging.INFO)
    logging.info('PrusaControll start')
    app = QtGui.QApplication(sys.argv)
    controller = Controller()
    window = controller.getView()
    app.exec_()
    logging.info('PrusaControll exit')