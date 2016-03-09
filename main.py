#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

import time
from PyQt4.QtGui import QPixmap, QSplashScreen

from controller import Controller
from gui import *
from sceneRender import *
from sceneData import *
from utilities import *

__author__ = 'Tibor Vavra'


if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	controller = Controller()
	window = controller.getView()
	sys.exit(app.exec_())