#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import os

from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt4 import *
from PyQt4 import QtGui

from PyQt4.QtCore import QDateTime, Qt
from PyQt4.QtGui import QDialog, QDateTimeEdit, QDialogButtonBox
from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtOpenGL import *
from PyQt4 import QtCore

import sceneRender

class SettingsDialog(QDialog):
	def __init__(self, controller, parent = None):
		super(SettingsDialog, self).__init__(parent)

		self.controller = controller

		layout = QVBoxLayout(self)

		# nice widget for editing the date
		self.languageLabel = QtGui.QLabel("Language")
		self.languageCombo = QtGui.QComboBox()
		#set enumeration
		self.languageCombo.addItem('en')
		self.languageCombo.addItem('cz')

		self.printerLabel = QtGui.QLabel("Printer model")
		self.printerCombo = QtGui.QComboBox()
		self.printerCombo.addItem('Prusa i3')
		self.printerCombo.addItem('Prusa i3 v2')

		layout.addWidget(self.languageLabel)
		layout.addWidget(self.languageCombo)

		layout.addWidget(self.printerLabel)
		layout.addWidget(self.printerCombo)

		# OK and Cancel buttons
		buttons = QDialogButtonBox(
			QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
		Qt.Horizontal, self)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)

	@staticmethod
	def getSettingsData(parent = None):
		dialog = SettingsDialog(parent)
		result = dialog.exec_()
		data = dialog.languageCombo.currentIndex()
		return (data, result == QDialog.Accepted)


class PrusaControllView(QtGui.QMainWindow):
	def __init__(self, c):
		self.controller = c
		super(PrusaControllView, self).__init__()
		self.setAcceptDrops(True)

		self.prusaControllWidget = PrusaControllWidget(self)
		self.setCentralWidget(self.prusaControllWidget)

		self.menubar = self.menuBar()
		#file menu definition
		self.fileMenu = self.menubar.addMenu('&File')
		self.fileMenu.addAction('Open project', self.controller.openProjectFile)
		self.fileMenu.addAction('Save project', self.controller.saveProjectFile)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction('Import stl file', self.controller.openModelFile)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction('Close', self.controller.close)

		#file menu definition

		#Settings menu
		self.settingsMenu = self.menubar.addMenu('&Settings')
		self.settingsMenu.addAction('PrusaControll settings', self.controller.openSettings)
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

	def openSettingsDialog(self):
		data, ok = SettingsDialog.getSettingsData()
		return data

	def disableSaveGcodeButton(self):
		self.prusaControllWidget.disableSaveGcodeButton()

	def enableSaveGcodeButton(self):
		self.prusaControllWidget.enableSaveGcodeButton()

	def openProjectFileDialog(self):
		filters = "Prus (*.prus *.PRUS)"
		title = 'Open project file'
		openAt = "/home"
		data = QtGui.QFileDialog.getOpenFileName(None, title, openAt, filters)
		return data

	def openModelFileDialog(self):
		filters = "STL (*.stl *.STL)"
		title = "Import stl file"
		openAt = "/home"
		data = QtGui.QFileDialog.getOpenFileName(None, title, openAt, filters)
		return data

	def saveProjectFileDialog(self):
		filters = "Prus (*.prus *.PRUS)"
		title = 'Save project file'
		openAt = "/home"
		data = QtGui.QFileDialog.getSaveFileName(None, title, openAt, filters)
		return data

	def saveGCondeFileDialog(self):
		filters = "gcode (*.gcode *.GCODE)"
		title = 'Save G-Code file'
		openAt = "/home"
		data = QtGui.QFileDialog.getSaveFileName(None, title, openAt, filters)
		return data


	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls():
			event.acceptProposedAction()
		else:
			super(PrusaControllView, self).dragEnterEvent(event)

	def dragMoveEvent(self, event):
		super(PrusaControllView, self).dragMoveEvent(event)

	def dropEvent(self, event):
		if event.mimeData().hasUrls():
			for url in event.mimeData().urls():
				self.statusBar().showMessage('Dropped file name is ' + str(url.path()))
				self.controller.openFile(url.path())
			event.acceptProposedAction()
		else:
			super(PrusaControllView, self).dropEvent(event)


class PrusaControllWidget(QtGui.QWidget):
	def __init__(self, parent=None):
		QtGui.QWidget.__init__(self, parent)
		if parent:
			self.parent = parent
			self.controller = parent.controller
		else:
			self.parent = None
			self.controller = None

		self.infillValue = 20

		self.initGUI()

	def initGUI(self):
		self.glWidget = sceneRender.GLWidget(self)

		self.tabWidget = QtGui.QTabWidget()

		self.toolTab = QtGui.QWidget()
		self.printTab = QtGui.QWidget()

		#tool tab
		self.selectButton = QtGui.QPushButton("Select")
		self.moveButton = QtGui.QPushButton("Move")
		self.rotateButton = QtGui.QPushButton("Rotate")
		self.scaleButton = QtGui.QPushButton("Scale")

		self.toolButtonGroup = QtGui.QButtonGroup()
		self.toolButtonGroup.setExclusive(True)

		self.toolButtonGroup.addButton(self.selectButton)
		self.toolButtonGroup.addButton(self.moveButton)
		self.toolButtonGroup.addButton(self.rotateButton)
		self.toolButtonGroup.addButton(self.scaleButton)

		self.selectButton.setCheckable(True)
		self.moveButton.setCheckable(True)
		self.rotateButton.setCheckable(True)
		self.scaleButton.setCheckable(True)

		self.toolTabVLayout = QtGui.QVBoxLayout()
		self.toolTabVLayout.addWidget(self.selectButton)
		self.toolTabVLayout.addWidget(self.moveButton)
		self.toolTabVLayout.addWidget(self.rotateButton)
		self.toolTabVLayout.addWidget(self.scaleButton)
		self.toolTabVLayout.addItem(QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))

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

		self.infillLabel = QtGui.QLabel("Infill %s" % str(self.infillValue)+'%')
		self.infillSlider = self.createSlider(self.setInfill, self.infillValue)

		self.supportCheckBox = QtGui.QCheckBox("Support material")
		self.brimCheckBox = QtGui.QCheckBox("Brim")

		self.progressBar = QtGui.QProgressBar()
		self.progressBar.setMinimum(0)
		self.progressBar.setMaximum(100)
		self.progressBar.setValue(0)

		self.generateButton = QtGui.QPushButton("Generate")

		#printing info place
		self.printingInfoLabel = QtGui.QLabel("Print info:")



		self.saveGCodeButton = QtGui.QPushButton("Save G-Code")
		self.saveGCodeButton.clicked.connect(self.controller.saveGCodeFile)


		self.printTabVLayout = QtGui.QVBoxLayout()
		self.printTabVLayout.addWidget(self.materialLabel)
		self.printTabVLayout.addWidget(self.materialCombo)
		self.printTabVLayout.addWidget(self.qualityLabel)
		self.printTabVLayout.addWidget(self.qualityCombo)
		self.printTabVLayout.addWidget(self.infillLabel)
		self.printTabVLayout.addWidget(self.infillSlider)
		self.printTabVLayout.addWidget(self.supportCheckBox)
		self.printTabVLayout.addWidget(self.brimCheckBox)
		self.printTabVLayout.addWidget(self.progressBar)
		self.printTabVLayout.addWidget(self.generateButton)
		self.printTabVLayout.addWidget(self.printingInfoLabel)
		self.printTabVLayout.addItem(QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))

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

	def disableSaveGcodeButton(self):
		self.saveGCodeButton.setDisabled(True)

	def enableSaveGcodeButton(self):
		self.saveGCodeButton.setDisabled(False)

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




'''
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
'''


