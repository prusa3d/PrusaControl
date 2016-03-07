# -*- coding: utf-8 -*-
import numpy
from abc import ABCMeta, abstractmethod
from stl.mesh import Mesh
from random import randint
import math
import itertools

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from copy import deepcopy


glutInit()

class AppScene(object):
	'''
	Class holding data of scene, models, positions, parameters
	it can be used for generating sliced data and rendering data
	'''
	def __init__(self):
		self.sceneZero = [.0, .0, .0]
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
		self.boundingSphereSize = .0
		self.boundingSphereCenter = [.0, .0, .0]
		self.boundingMinimalPoint = [.0, .0, .0]
		self.zeroPoint = [.0, .0, .0]
		self.min = [.0,.0,.0]
		self.max = [.0,.0,.0]


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


	def normalizeObject(self):
		sceneCenter = Vector(a=Vector().getRaw(), b=self.zeroPoint)
		print(str(sceneCenter.getRaw()))
		self.v0 = [ Vector().minusAB(v, sceneCenter.getRaw())  for v in self.v0]
		self.v1 = [ Vector().minusAB(v, sceneCenter.getRaw())  for v in self.v1]
		self.v2 = [ Vector().minusAB(v, sceneCenter.getRaw())  for v in self.v2]

		self.max = Vector().minusAB(self.max, sceneCenter.getRaw())
		self.min = Vector().minusAB(self.min, sceneCenter.getRaw())

		self.boundingSphereCenter = Vector().minusAB(self.boundingSphereCenter, sceneCenter.getRaw())
		self.zeroPoint = Vector().minusAB(self.zeroPoint, sceneCenter.getRaw())
		self.zeroPoint[2] = self.min[2]


	def render(self, debug=False):
		if debug:
			glDisable(GL_DEPTH_TEST)

			glBegin(GL_POINTS)
			glColor3f(0,1,0)
			glVertex3f(self.boundingSphereCenter[0], self.boundingSphereCenter[1], self.boundingSphereCenter[2])
			glColor3f(0,0,1)
			glVertex3f(self.zeroPoint[0], self.zeroPoint[1], self.zeroPoint[2])
			glEnd()
			glEnable(GL_DEPTH_TEST)
			glPushMatrix()
			glTranslated(self.boundingSphereCenter[0], self.boundingSphereCenter[1], self.boundingSphereCenter[2])
			glLineWidth(1)
			glColor3f(.25, .25, .25)
			glutWireSphere(self.boundingSphereSize+0.1, 16, 10)
			glPopMatrix()

		if self.selected:
			glColor3f(.5,0,0)
		else:
			glColor3f(self.color[0], self.color[1], self.color[2])
		glCallList(self.displayList)


	def makeDisplayList(self):
		genList = glGenLists(1)
		glNewList(genList, GL_COMPILE)

		glBegin(GL_TRIANGLES)
		for i in xrange(len(self.v0)):
			glNormal3d(self.newNormal[i][0], self.newNormal[i][1], self.newNormal[i][2])
			glVertex3d(self.v0[i][0], self.v0[i][1], self.v0[i][2])
			glVertex3d(self.v1[i][0], self.v1[i][1], self.v1[i][2])
			glVertex3d(self.v2[i][0], self.v2[i][1], self.v2[i][2])
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

		'''
		some magic with model data...
		I need normals, transformations...
		'''

		#calculate bounding sphere
		'''
		model.max[0] = max([a[0]*.1 for a in mesh.points])
		model.min[0] = min([a[0]*.1 for a in mesh.points])
		model.boundingSphereCenter[0] = (model.max[0] + model.min[0]) * .5

		model.max[1] = max([a[1]*.1 for a in mesh.points])
		model.min[1] = min([a[1]*.1 for a in mesh.points])
		model.boundingSphereCenter[1] = (model.max[1] + model.min[1]) * .5

		model.max[2] = max([a[2]*.1 for a in mesh.points])
		model.min[2] = min([a[2]*.1 for a in mesh.points])
		model.boundingSphereCenter[2] = (model.max[2] + model.min[2]) * .5

		model.zeroPoint = deepcopy(model.boundingSphereCenter)
		model.zeroPoint[2] = model.min[2]

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

			normal = mesh.normals[i]
			l = numpy.linalg.norm(normal)
			normal[0] = normal[0] / l
			normal[1] = normal[1] / l
			normal[2] = normal[2] / l

			model.newNormal.append(normal)

		model.normalizeObject()
		model.displayList = model.makeDisplayList()
		'''

		model.newNormal = mesh.normals
		model.newNormal = model.newNormal/numpy.linalg.norm(mesh.normals)
		model.v0 = mesh.v0*.1
		model.v1 = mesh.v1*.1
		model.v2 = mesh.v2*.1

		#TODO:Zrychlit tuto cast
		model.max[0] = numpy.max([a[0] for a in itertools.chain(model.v0, model.v1, model.v2)])
		model.min[0] = numpy.min([a[0] for a in itertools.chain(model.v0, model.v1, model.v2)])
		model.boundingSphereCenter[0] = (model.max[0] + model.min[0]) * .5

		model.max[1] = numpy.max([a[1] for a in itertools.chain(model.v0, model.v1, model.v2)])
		model.min[1] = numpy.min([a[1] for a in itertools.chain(model.v0, model.v1, model.v2)])
		model.boundingSphereCenter[1] = (model.max[1] + model.min[1]) * .5

		model.max[2] = numpy.max([a[2] for a in itertools.chain(model.v0, model.v1, model.v2)])
		model.min[2] = numpy.min([a[2] for a in itertools.chain(model.v0, model.v1, model.v2)])
		model.boundingSphereCenter[2] = (model.max[2] + model.min[2]) * .5

		model.zeroPoint = deepcopy(model.boundingSphereCenter)
		model.zeroPoint[2] = model.min[2]

		model.normalizeObject()

		v = Vector(model.boundingSphereCenter)
		for vert in itertools.chain(model.v0, model.v1, model.v2):
			vL = abs(v.lenght(vert))

			if vL > model.boundingSphereSize:
				model.boundingSphereSize = vL

		model.displayList = model.makeDisplayList()


		return model


#math
class Vector(object):
	def __init__(self, v=[.0, .0, .0], a=[], b=[]):
		if a and b:
			self.x = b[0]-a[0]
			self.y = b[1]-a[1]
			self.z = b[2]-a[2]
		else:
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

	@staticmethod
	def minusAB(a, b):
		c =[0,0,0]
		c[0] = a[0]-b[0]
		c[1] = a[1]-b[1]
		c[2] = a[2]-b[2]
		return c