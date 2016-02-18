# -*- coding: utf-8 -*-
import numpy
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
		self.models = []

	def clearScene(self):
		self.models = []



class Model(object):
	'''
	this is reprezentation of model data, data readed from file
	'''
	def __init__(self):
		#structural data
		self.v0 = []
		self.v1 = []
		self.v2 = []
		self.normal = []
		self.newNormal = []
		self.displayList = []

		#transformation data
		self.pos = [.0,.0,.0]
		self.rot = [.0,.0,.0]
		self.scale = [.0,.0,.0]

		#helping data
		self.selected = False
		self.boundingSphereCenter = [.0, .0, .0]
		self.boundingSphereSize = .0
		self.zeroPoint = [.0, .0, .0]

		self.color = [randint(3, 8) * 0.1,
					  randint(3, 8) * 0.1,
					  randint(3, 8) * 0.1]


	def closestPoint(self, a, b, p):

		ab = Vector([b.x-a.x, b.y-a.y, b.z-a.z])
		abSquare = numpy.dot(ab.getRaw(), ab.getRaw())
		ap = Vector([p.x-a.x, p.y-a.y, p.z-a.z])
		apDotAB = numpy.dot(ap.getRaw(), ab.getRaw())
		t = apDotAB / abSquare
		q = Vector([a.x+ab.x*t, a.y+ab.y*t, a.z+ab.z*t])
		return q


	def intersectionRayBoundingSphere(self, start, end):
		pt = self.closestPoint(Vector(start), Vector(end), Vector(self.boundingSphereCenter))
		lenght = pt.lenght(self.boundingSphereCenter)
		return lenght < self.boundingSphereSize



	def intersectionRayModel(self, rayStart, rayEnd):
		w = Vector(rayEnd)
		w.minus(rayStart)
		w.normalize()

		for i in xrange(len(self.v0)):
			b = [.0,.0,.0]
			e1 = Vector(self.v1[i])
			e1.minus(self.v0[i])
			e2 = Vector(self.v2[i])
			e2.minus(self.v0[i])

			n = Vector(self.newNormal[i])

			q = numpy.cross(w.getRaw(), e2.getRaw())
			a = numpy.dot(e1.getRaw(), q)

			if((numpy.dot(n.getRaw(), w.getRaw())>= .0) or (abs(a) <=.0001)):
				continue
				#return False

			s = Vector(rayStart)
			s.minus(self.v0[i])
			s.sqrt(a)

			r = numpy.cross(s.getRaw(), e1.getRaw())
			b[0] = numpy.dot(s.getRaw(), q)
			b[1] = numpy.dot(r, w.getRaw())
			b[2] = 1.0 - b[0] - b[1]

			if ((b[0] < .0) or (b[1] < .0) or (b[2] < .0)):
				continue
				#return False

			t = numpy.dot(e2.getRaw(), r)
			if (t >= .0):
				return True
			else:
				continue
		return False




	def render(self):
		if self.selected:
			glColor3f(1,0,0)
		else:
			glColor3f(self.color[0], self.color[1], self.color[2])
		glCallList(self.displayList)


	def makeDisplayList(self):
		genList = glGenLists(1)
		glNewList(genList, GL_COMPILE)

		#glColor3f(self.color[0], self.color[1], self.color[2])
		glBegin(GL_TRIANGLES)
		for i in xrange(len(self.v0)):
			glNormal3d(self.newNormal[i][0], self.newNormal[i][1], self.newNormal[i][2])
			glVertex3d(self.v0[i][0], self.v0[i][1], self.v0[i][2])
			glVertex3d(self.v1[i][0], self.v1[i][1], self.v1[i][2])
			glVertex3d(self.v2[i][0], self.v2[i][1], self.v2[i][2])
		glEnd()

		glPointSize(4.0)
		glDisable(GL_DEPTH_TEST)
		glColor3f(1,0,1)
		glBegin(GL_POINTS)
		glVertex3d(self.boundingSphereCenter[0], self.boundingSphereCenter[1], self.boundingSphereCenter[2])
		glEnd()
		glEnable(GL_DEPTH_TEST)
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

		'''
		some magic with model data...
		I need normals, transformations...
		'''

		#calculate bounding sphere
		xMax = max([a[0]*.1 for a in mesh.points])
		xMin = min([a[0]*.1 for a in mesh.points])
		model.boundingSphereCenter[0] = (xMax + xMin) * .5


		yMax = max([a[1]*.1 for a in mesh.points])
		yMin = min([a[1]*.1 for a in mesh.points])
		model.boundingSphereCenter[1] = (yMax + yMin) * .5

		zMax = max([a[2]*.1 for a in mesh.points])
		zMin = min([a[2]*.1 for a in mesh.points])
		model.boundingSphereCenter[2] = (zMax + zMin) * .5

		model.zeroPoint = model.boundingSphereCenter
		model.zeroPoint[2] = .0

		for i in xrange(len(mesh.v0)):
			normal = [.0, .0, .0]
			mv0 = mesh.v0[i]*0.1
			mv1 = mesh.v1[i]*0.1
			mv2 = mesh.v2[i]*0.1

			model.v0.append(mv0)
			model.v1.append(mv1)
			model.v2.append(mv2)

			v0 = Vector(model.boundingSphereCenter)
			v1 = Vector(model.boundingSphereCenter)
			v2 = Vector(model.boundingSphereCenter)

			v0L = abs(v0.lenght(mv0))
			v1L = abs(v1.lenght(mv1))
			v2L = abs(v2.lenght(mv2))

			if v0L > model.boundingSphereSize:
				model.boundingSphereSize = v0L
			if v1L > model.boundingSphereSize:
				model.boundingSphereSize = v1L
			if v2L > model.boundingSphereSize:
				model.boundingSphereSize = v2L

			'''
			uX = mesh.v1[i][0] - mesh.v0[i][0]
			uY = mesh.v1[i][1] - mesh.v0[i][1]
			uZ = mesh.v1[i][2] - mesh.v0[i][2]

			vX = mesh.v2[i][0] - mesh.v0[i][0]
			vY = mesh.v2[i][1] - mesh.v0[i][1]
			vZ = mesh.v2[i][2] - mesh.v0[i][2]

			normal[0] = (uY*vZ) - (uZ*vY)
			normal[1] = (uZ*vX) - (uX*vZ)
			normal[2] = (uX*vY) - (uY*vX)
			'''

			normal = mesh.normals[i]
			l = math.sqrt((normal[0] * normal[0]) + (normal[1] * normal[1]) + (normal[2] * normal[2]))
			normal[0] = (normal[0]*1.0) / (l*1.0)
			normal[1] = (normal[1]*1.0) / (l*1.0)
			normal[2] = (normal[2]*1.0) / (l*1.0)

			model.newNormal.append(normal)
			model.normal.append(mesh.normals[i])



		model.displayList = model.makeDisplayList()

		return model


#math
class Vector(object):
	def __init__(self, v=[.0, .0, .0]):
		self.x = v[0]
		self.y = v[1]
		self.z = v[2]

	def minus(self, v):
		self.x -= v[0]
		self.y -= v[1]
		self.z -= v[2]

	def sqrt(self, n):
		self.x /= n
		self.y /= n
		self.z /= n

	def plus(self, v):
		self.x += v[0]
		self.y += v[1]
		self.z += v[2]

	def normalize(self):
		l = self.len()
		self.x /= l
		self.y /= l
		self.z /= l


	def lenght(self, v):
		x = v[0] - self.x
		y = v[1] - self.y
		z = v[2] - self.z
		return math.sqrt((x*x)+(y*y)+(z*z))

	def len(self):
		x = self.x
		y = self.y
		z = self.z
		return math.sqrt((x*x)+(y*y)+(z*z))

	def getRaw(self):
		return [self.x, self.y, self.z]