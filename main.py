#!/usr/bin/env python
# -*- coding: utf-8 -*-


from stl import *

import kivy
from kivy.app import App

from sceneRender import *

__author__ = 'Tibor Vavra'

kivy.require('1.9.0')


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
	f = Open('z.stl', 'r')
	data = stl.read_binary_file(f)
	print(str(data))
'''

class PrusaControllApp(App):
	kv_directory = 'gui'

	def build(self):
		return PrusaControllWidget()

if __name__ == "__main__":
	PrusaControllApp().run()
