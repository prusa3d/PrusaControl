# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
from stl.mesh import Mesh
from random import randint
import math

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
		self.newNormal = []
		self.color = [randint(1,10)*0.1,
					  randint(3,8)*0.1,
					  randint(1,10)*0.1]

	def makeDisplayList(self):
		genList = glGenLists(1)
		glNewList(genList, GL_COMPILE)

		glColor3f(self.color[0], self.color[1], self.color[2])
		glBegin(GL_TRIANGLES)

		for i in xrange(len(self.v0)):
			glNormal3f(self.newNormal[i][0], self.newNormal[i][1], self.newNormal[i][2])
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
			normal = [.0, .0, .0]
			model.v0.append(mesh.v0[i]*0.1)
			model.v1.append(mesh.v1[i]*0.1)
			model.v2.append(mesh.v2[i]*0.1)

			uX = mesh.v1[i][0] - mesh.v0[i][0]
			uY = mesh.v1[i][1] - mesh.v0[i][1]
			uZ = mesh.v1[i][2] - mesh.v0[i][2]

			vX = mesh.v2[i][0] - mesh.v0[i][0]
			vY = mesh.v2[i][1] - mesh.v0[i][1]
			vZ = mesh.v2[i][2] - mesh.v0[i][2]

			normal[0] = (uY*vZ) - (uZ*vY)
			normal[1] = (uZ*vX) - (uX*vZ)
			normal[2] = (uX*vY) - (uY*vX)

			l = math.sqrt((normal[0] * normal[0]) + (normal[1] * normal[1]) + (normal[2] * normal[2]))
			normal[0] = (normal[0]*1.0) / (l*1.0)
			normal[1] = (normal[1]*1.0) / (l*1.0)
			normal[2] = (normal[2]*1.0) / (l*1.0)

			model.newNormal.append(normal)
			model.normal.append(mesh.normals[i])

		'''
		some magic with model data...
		I need normals, transformations...
		'''
		return model


