#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

from controller import Controller
from gui import *
from sceneRender import *
from sceneData import *
from utilities import *

__author__ = 'Tibor Vavra'



class TestUM:
	def setup(self):
		print ("TestUM:setup() before each test method")

	def teardown(self):
		print ("TestUM:teardown() after each test method")

	@classmethod
	def setup_class(cls):
		print ("setup_class() before any methods in this class")

	@classmethod
	def teardown_class(cls):
		print ("teardown_class() after any methods in this class")

	def test_numbers_5_6(self):
		print 'test_numbers_5_6()  <============================ actual test code'

	def test_strings_b_2(self):
		print 'test_strings_b_2()  <============================ actual test code'


'''
if __name__ == "__main__":
	app = QtGui.QApplication(['Yo'])
	window = PrusaControllWidget()
	window.show()
	app.exec_()
'''

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	controller = Controller()
	window = controller.getView()
	#window.show()
	sys.exit(app.exec_())