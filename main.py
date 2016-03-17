#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import Controller
from sceneRender import *
from sceneData import *
import logging

__author__ = 'Tibor Vavra'


def main():
    logging.info('PrusaControll start')
    app = QtGui.QApplication(sys.argv)
    controller = Controller()
    window = controller.getView()
    app.exec_()
    logging.info('PrusaControll exit')


if __name__ == '__main__':
    FORMAT = "[%(levelname)s][%(filename)s:%(lineno)s:%(funcName)s()]-%(message)s"
    logging.basicConfig(format=FORMAT, filename='info.log', filemode='w', level=logging.DEBUG)
    main()