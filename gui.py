#!/usr/bin/env python


import math
import os

from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt4 import *
from PyQt4 import QtGui
from PyQt4.QtOpenGL import *
from PyQt4 import QtCore



class PrusaControll(QtGui.QMainWindow):
	def __init__(self):
		super(PrusaControll, self).__init__()
		self.setAcceptDrops(True)
		#self.setDragDropMode(QAbstractItemView.InternalMove)

		self.prusaControllWidget = PrusaControllWidget(self)
		self.setCentralWidget(self.prusaControllWidget)

		self.menubar = self.menuBar()
		#file menu definition
		self.fileMenu = self.menubar.addMenu('&File')
		self.fileMenu.addAction('Open project', self.openProjectFile)
		self.fileMenu.addAction('Save project', self.saveProjectFile)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction('Import stl file', self.openStlFile)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction('Close')
		#file menu definition

		#Settings menu
		self.settingsMenu = self.menubar.addMenu('&Settings')
		self.settingsMenu.addAction('PrusaControll Settings')
		#Settings menu

		#Help menu
		self.helpMenu = self.menubar.addMenu('&Help')
		self.helpMenu.addAction('Help')
		self.helpMenu.addAction('Prusa Online')
		self.helpMenu.addSeparator()
		self.helpMenu.addAction('About')
		#Help menu


		self.statusBar().showMessage('Ready')
		self.setWindowTitle(self.tr("PrusaControll"))
		self.show()

	def openProjectFile(self):
		filters = "Prus (*.prus *.PRUS)"
		title = 'Open project file'
		openAt = "/home"
		filepath = QtGui.QFileDialog.getOpenFileName(None, title, openAt, filters)
		print(str(filepath))
		self.statusBar().showMessage('file path: ' + str(filepath))

	def openStlFile(self):
		filters = "STL (*.stl *.STL)"
		title = "Import stl file"
		openAt = "/home"
		data = QtGui.QFileDialog.getOpenFileName(None, title, openAt, filters)
		print(str(data))
		self.statusBar().showMessage('file path: ' + str(data))

	def saveProjectFile(self):
		filters = "Prus (*.prus *.PRUS)"
		title = 'Save project file'
		openAt = "/home"
		data = QtGui.QFileDialog.getSaveFileName(None, title, openAt, filters)
		print(str(data))
		self.statusBar().showMessage('file path: ' + str(data))

	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls():
			event.acceptProposedAction()
		else:
			super(PrusaControll, self).dragEnterEvent(event)

	def dragMoveEvent(self, event):
		super(PrusaControll, self).dragMoveEvent(event)

	def dropEvent(self, event):
		if event.mimeData().hasUrls():
			for url in event.mimeData().urls():
				self.statusBar().showMessage('Dropped file name is ' + str(url.path()))
			event.acceptProposedAction()
		else:
			super(PrusaControll, self).dropEvent(event)


class PrusaControllWidget(QtGui.QWidget):
	def __init__(self, parent=None):
		QtGui.QWidget.__init__(self, parent)

		self.infillValue = 20

		self.initGUI()

	def initGUI(self):
		self.glWidget = GLWidget()

		self.tabWidget = QtGui.QTabWidget()

		self.toolTab = QtGui.QWidget()
		self.printTab = QtGui.QWidget()

		#tool tab
		self.moveButton = QtGui.QPushButton("Move")
		self.rotateButton = QtGui.QPushButton("Rotate")
		self.scaleButton = QtGui.QPushButton("Scale")

		self.toolTabVLayout = QtGui.QVBoxLayout()
		self.toolTabVLayout.addWidget(self.moveButton)
		self.toolTabVLayout.addWidget(self.rotateButton)
		self.toolTabVLayout.addWidget(self.scaleButton)
		self.toolTabVLayout.addItem(QtGui.QSpacerItem(0,0,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding))

		self.toolTab.setLayout(self.toolTabVLayout)
		#tool tab

		#print tab
		self.materialLabel = QtGui.QLabel("Material")
		self.materialCombo = QtGui.QComboBox()
		#set enumeration
		self.materialCombo.addItem('ABS')
		self.materialCombo.addItem('PLA')

		self.qualityLabel = QtGui.QLabel("Quality")
		self.qualityCombo = QtGui.QComboBox()
		#set enumeration
		self.qualityCombo.addItem('High')
		self.qualityCombo.addItem('Medium')
		self.qualityCombo.addItem('Low')

		self.infillLabel = QtGui.QLabel("Infill 20%")
		self.infillSlider = self.createSlider(self.setInfill, self.infillValue)

		self.supportCheckBox = QtGui.QCheckBox("Support material")
		self.brimCheckBox = QtGui.QCheckBox("Brim")

		self.generateButton = QtGui.QPushButton("Generate")
		self.saveGCodeButton = QtGui.QPushButton("Save G-Code")

		self.printTabVLayout = QtGui.QVBoxLayout()
		self.printTabVLayout.addWidget(self.materialLabel)
		self.printTabVLayout.addWidget(self.materialCombo)
		self.printTabVLayout.addWidget(self.qualityLabel)
		self.printTabVLayout.addWidget(self.qualityCombo)
		self.printTabVLayout.addWidget(self.infillLabel)
		self.printTabVLayout.addWidget(self.infillSlider)
		self.printTabVLayout.addWidget(self.supportCheckBox)
		self.printTabVLayout.addWidget(self.brimCheckBox)
		self.printTabVLayout.addItem(QtGui.QSpacerItem(0,0,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding))
		self.printTabVLayout.addWidget(self.generateButton)
		self.printTabVLayout.addWidget(self.saveGCodeButton)

		self.printTab.setLayout(self.printTabVLayout)
		#print tab

		self.tabWidget.addTab(self.toolTab, "Tools")
		self.tabWidget.addTab(self.printTab, "Print")
		self.tabWidget.setMaximumWidth(300)

		mainLayout = QtGui.QHBoxLayout()
		mainLayout.addWidget(self.glWidget)
		mainLayout.addWidget(self.tabWidget)

		self.setLayout(mainLayout)

		self.show()

	def setInfill(self, val):
		self.infillValue = val
		self.infillLabel.setText("Infill " + str(val) + "%")



	def createSlider(self, setterSlot, defaultValue=0):
		slider = QtGui.QSlider(QtCore.Qt.Horizontal)

		slider.setRange(0, 100)
		slider.setSingleStep(10)
		slider.setPageStep(20)
		slider.setTickInterval(10)
		slider.setValue(defaultValue)
		slider.setTickPosition(QtGui.QSlider.TicksRight)

		self.connect(slider, QtCore.SIGNAL("valueChanged(int)"), setterSlot)
		return slider


class GLWidget(QGLWidget):
	def __init__(self, parent=None):
		QGLWidget.__init__(self, parent)

		self.object = 0
		self.xRot = 0
		self.yRot = 0
		self.zRot = 0

		self.lastPos = QtCore.QPoint()

		self.trolltechGreen = QtGui.QColor.fromCmykF(0.40, 0.0, 1.0, 0.0)
		self.trolltechPurple = QtGui.QColor.fromCmykF(0.39, 0.15, 0.0, 0.0)

	def xRotation(self):
		return self.xRot

	def yRotation(self):
		return self.yRot

	def zRotation(self):
		return self.zRot

	def minimumSizeHint(self):
		return QtCore.QSize(50, 50)

	def sizeHint(self):
		return QtCore.QSize(400, 400)

	def setXRotation(self, angle):
		angle = self.normalizeAngle(angle)
		if angle != self.xRot:
			self.xRot = angle
			self.emit(QtCore.SIGNAL("xRotationChanged(int)"), angle)
			self.updateGL()

	def setYRotation(self, angle):
		angle = self.normalizeAngle(angle)
		if angle != self.yRot:
			self.yRot = angle
			self.emit(QtCore.SIGNAL("yRotationChanged(int)"), angle)
			self.updateGL()

	def setZRotation(self, angle):
		angle = self.normalizeAngle(angle)
		if angle != self.zRot:
			self.zRot = angle
			self.emit(QtCore.SIGNAL("zRotationChanged(int)"), angle)
			self.updateGL()

	def initializeGL(self):
		self.qglClearColor(self.trolltechPurple.darker())
		self.object = self.makeObject()
		glShadeModel(GL_FLAT)
		glEnable(GL_DEPTH_TEST)
		glEnable(GL_CULL_FACE)

	def paintGL(self):
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		glLoadIdentity()
		glTranslated(0.0, 0.0, -10.0)
		glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
		glRotated(self.yRot / 16.0, 0.0, 1.0, 0.0)
		glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)
		glCallList(self.object)

	def resizeGL(self, width, height):
		side = min(width, height)
		glViewport((width - side) / 2, (height - side) / 2, side, side)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		glOrtho(-0.5, +0.5, +0.5, -0.5, 4.0, 15.0)
		glMatrixMode(GL_MODELVIEW)

	def mousePressEvent(self, event):
		self.lastPos = QtCore.QPoint(event.pos())

	def mouseMoveEvent(self, event):
		dx = event.x() - self.lastPos.x()
		dy = event.y() - self.lastPos.y()

		if event.buttons() & QtCore.Qt.LeftButton:
			self.setXRotation(self.xRot + 8 * dy)
			self.setYRotation(self.yRot + 8 * dx)
		elif event.buttons() & QtCore.Qt.RightButton:
			self.setXRotation(self.xRot + 8 * dy)
			self.setZRotation(self.zRot + 8 * dx)

		self.lastPos = QtCore.QPoint(event.pos())

	def makeObject(self):
		genList = glGenLists(1)
		glNewList(genList, GL_COMPILE)

		glBegin(GL_QUADS)

		x1 = +0.06
		y1 = -0.14
		x2 = +0.14
		y2 = -0.06
		x3 = +0.08
		y3 = +0.00
		x4 = +0.30
		y4 = +0.22

		self.quad(x1, y1, x2, y2, y2, x2, y1, x1)
		self.quad(x3, y3, x4, y4, y4, x4, y3, x3)

		self.extrude(x1, y1, x2, y2)
		self.extrude(x2, y2, y2, x2)
		self.extrude(y2, x2, y1, x1)
		self.extrude(y1, x1, x1, y1)
		self.extrude(x3, y3, x4, y4)
		self.extrude(x4, y4, y4, x4)
		self.extrude(y4, x4, y3, x3)

		Pi = 3.14159265358979323846
		NumSectors = 200

		for i in range(NumSectors):
			angle1 = (i * 2 * Pi) / NumSectors
			x5 = 0.30 * math.sin(angle1)
			y5 = 0.30 * math.cos(angle1)
			x6 = 0.20 * math.sin(angle1)
			y6 = 0.20 * math.cos(angle1)

			angle2 = ((i + 1) * 2 * Pi) / NumSectors
			x7 = 0.20 * math.sin(angle2)
			y7 = 0.20 * math.cos(angle2)
			x8 = 0.30 * math.sin(angle2)
			y8 = 0.30 * math.cos(angle2)

			self.quad(x5, y5, x6, y6, x7, y7, x8, y8)

			self.extrude(x6, y6, x7, y7)
			self.extrude(x8, y8, x5, y5)

		glEnd()
		glEndList()

		return genList

	def quad(self, x1, y1, x2, y2, x3, y3, x4, y4):
		self.qglColor(self.trolltechGreen)

		glVertex3d(x1, y1, -0.05)
		glVertex3d(x2, y2, -0.05)
		glVertex3d(x3, y3, -0.05)
		glVertex3d(x4, y4, -0.05)

		glVertex3d(x4, y4, +0.05)
		glVertex3d(x3, y3, +0.05)
		glVertex3d(x2, y2, +0.05)
		glVertex3d(x1, y1, +0.05)

	def extrude(self, x1, y1, x2, y2):
		self.qglColor(self.trolltechGreen.darker(250 + int(100 * x1)))

		glVertex3d(x1, y1, +0.05)
		glVertex3d(x2, y2, +0.05)
		glVertex3d(x2, y2, -0.05)
		glVertex3d(x1, y1, -0.05)

	def normalizeAngle(self, angle):
		while angle < 0:
			angle += 360 * 16
		while angle > 360 * 16:
			angle -= 360 * 16
		return angle
