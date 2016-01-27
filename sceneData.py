# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
from stl.mesh import Mesh

from OpenGL.GL import *
from OpenGL.GLU import *


class AppScene(object):
	'''
	Class holding data of scene, models, positions, parameters
	it can be used for generating sliced data and rendering data
	'''
	def __init__(self):
		self.modelsData = []
		self.models = []

	def clearScene(self):
		self.modelsData = []
		self.models = []






class Model(object):
	'''
	this is reprezentation of model data, data readed from file
	'''
	def __init__(self):
		self.v0 = []
		self.v1 = []
		self.v2 = []
		self.normal = []
		#self.color = [rand(), rand(), rand()]

	def makeDisplayList(self):
		genList = glGenLists(1)
		glNewList(genList, GL_COMPILE)

		glBegin(GL_TRIANGLES)

		for i in xrange(len(self.v0)):
			glNormal3f(self.normal[i][0], self.normal[i][1], self.normal[i][2])
			glVertex3f(self.v0[i][0], self.v0[i][1], self.v0[i][2])
			glVertex3f(self.v1[i][0], self.v1[i][1], self.v1[i][2])
			glVertex3f(self.v2[i][0], self.v2[i][1], self.v2[i][2])

		glEnd()
		glEndList()

		return genList


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
	
	def load(self, filename):
		print "this is STL file reader"
		mesh = Mesh.from_file(filename)
		model = Model()

		for i in xrange(len(mesh.v0)):
			model.v0.append(mesh.v0[i]*0.1)
			model.v1.append(mesh.v1[i]*0.1)
			model.v2.append(mesh.v2[i]*0.1)
			model.normal.append(mesh.normals[i])

		'''
		some magic with model data...
		I need normals, transformations...
		'''
		return model


