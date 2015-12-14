# -*- coding: utf-8 -*-

from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt4 import QtGui
from PyQt4.QtOpenGL import *


class PrusaControllWidget2(QtGui.QWidget):
	'''
	Main widget of application
	'''

	def __init__(self):
		super(PrusaControllWidget, self).__init__()

		self.widget = glWidget(self)

		self.button = QtGui.QPushButton('Test', self)

		mainLayout = QtGui.QHBoxLayout()
		mainLayout.addWidget(self.widget)
		mainLayout.addWidget(self.button)

		self.setLayout(mainLayout)




class CenteredCamera(object):
	'''
	Special camera class, this camera is centered on scene and rotate around
	it can zoom in and out
	hanndle mouse events
	'''
	pass


class SceneRenderer(CenteredCamera):
	'''
	Scene Renderer widget, renderer designed for drawing a Scene data
	'''
	pass



class glWidget(QGLWidget):
	def __init__(self, parent):
		QGLWidget.__init__(self, parent)
		self.setMinimumSize(640, 480)

	def paintGL(self):


		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		glLoadIdentity()


		glTranslatef(-2.5, 0.5, -6.0)
		glColor3f( 1.0, 1.5, 0.0 );
		glPolygonMode(GL_FRONT, GL_FILL);

		glBegin(GL_TRIANGLES)
		glVertex3f(2.0,-1.2,0.0)
		glVertex3f(2.6,0.0,0.0)
		glVertex3f(2.9,-1.2,0.0)
		glEnd()

		glFlush()



	def initializeGL(self):



		glClearDepth(1.0)
		glDepthFunc(GL_LESS)
		glEnable(GL_DEPTH_TEST)
		glShadeModel(GL_SMOOTH)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		gluPerspective(45.0,1.33,0.1, 100.0)
		glMatrixMode(GL_MODELVIEW)



class Scene(object):
	'''
	Scene is class representing data from AppScene, it is simplificated data of scene, rendering is less important then printing
	'''
	pass
