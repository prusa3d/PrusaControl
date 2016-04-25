#!/opt/local/bin/python2.7
# -*- coding: utf-8 -*-
from PyQt4 import QtGui

from controller import Controller
from sceneRender import *
from sceneData import *
import logging
import profile


__author__ = 'Tibor Vavra'

DEBUG = False

def main():
    logging.info('PrusaControll start')
    app = QtGui.QApplication(sys.argv)
    controller = Controller(app)
    window = controller.get_view()
    app.exec_()
    logging.info('PrusaControll exit')


if __name__ == '__main__':
    FORMAT = "[%(levelname)s][%(filename)s:%(lineno)s:%(funcName)s()]-%(message)s"
    logging.basicConfig(format=FORMAT, filename='info.log', filemode='w', level=logging.DEBUG)

    if DEBUG:
        profile.run('main()')
    else:
        main()
