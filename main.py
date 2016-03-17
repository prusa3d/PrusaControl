#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Tibor Vavra'

from controller import Controller
from sceneRender import *
from sceneData import *

import logging
import logging.config


if __name__ == '__main__':
    logging.basicConfig(filename="info.log", filemode='w', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    logging.info('PrusaControll start')
    app = QtGui.QApplication(sys.argv)
    controller = Controller()
    window = controller.getView()
    app.exec_()
    logging.info('PrusaControll end')
