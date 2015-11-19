# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
from stl import mesh



class AppScene(object):
	'''
	Class holding data of scene, models, positions, parameters
	it can be used for generating sliced data and rendering data
	'''
	pass


class Model(object):
	'''
	this is reprezentation of model data, data readed from file
	'''
	pass


class ModelTypeAbstract(object):
	'''
	model type is abstract class, reprezenting reading of specific model data file
	'''
	__metaclass__ = ABCMeta

	def __init__(self):
		pass

	@abstractmethod
	def load(filename):
		print "This is abstract model type"
		return None



class ModelTypeStl(ModelTypeAbstract):
	'''
	Concrete ModelType class for STL type file, it can load binary and char file
	'''
	
	def load(filename):
		print "this is STL file reader"
		mesh = mesh.Mesh.from_file(filename)
		
		model = Model()


