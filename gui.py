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
		self.languageCombo.addItems(self.controller.enumeration['language'].values())
		self.languageCombo.setCurrentIndex(self.controller.enumeration['language'].keys().index(self.controller.settings['language']))

		self.printerLabel = QtGui.QLabel("Printer model")
		self.printerCombo = QtGui.QComboBox()
		self.printerCombo.addItems(self.controller.enumeration['printer'].values())
		self.printerCombo.setCurrentIndex(self.controller.enumeration['printer'].keys().index(self.controller.settings['printer']))

		self.debugCheckBox = QtGui.QCheckBox("Debug")
		self.debugCheckBox.setChecked(self.controller.settings['debug'])

		layout.addWidget(self.languageLabel)
		layout.addWidget(self.languageCombo)

		layout.addWidget(self.printerLabel)
		layout.addWidget(self.printerCombo)

		layout.addWidget(self.debugCheckBox)

		# OK and Cancel buttons
		buttons = QDialogButtonBox(
			QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
		Qt.Horizontal, self)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)

	@staticmethod
	def getSettingsData(controller, parent = None):
		data = {}
		dialog = SettingsDialog(controller, parent)
		result = dialog.exec_()
		data['language'] = controller.enumeration['language'].keys()[dialog.languageCombo.currentIndex()]
		data['printer'] = controller.enumeration['printer'].keys()[dialog.printerCombo.currentIndex()]
		data['debug'] = dialog.debugCheckBox.isChecked()
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
		self.fileMenu.addAction('Reset', self.controller.resetScene)
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
		data, ok = SettingsDialog.getSettingsData(self.controller, self.parent())
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
		data = self.convertFilePathToUnicode(data)
		return data

	def openModelFileDialog(self):
		filters = "STL (*.stl *.STL)"
		title = "Import stl file"
		openAt = "/home"
		data = QtGui.QFileDialog.getOpenFileName(None, title, openAt, filters)
		data = self.convertFilePathToUnicode(data)
		return data

	def saveProjectFileDialog(self):
		filters = "Prus (*.prus *.PRUS)"
		title = 'Save project file'
		openAt = "/home"
		data = QtGui.QFileDialog.getSaveFileName(None, title, openAt, filters)
		data = self.convertFilePathToUnicode(data)
		return data

	def saveGCondeFileDialog(self):
		filters = "gcode (*.gcode *.GCODE)"
		title = 'Save G-Code file'
		openAt = "/home"
		data = QtGui.QFileDialog.getSaveFileName(None, title, openAt, filters)
		data = self.convertFilePathToUnicode(data)
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
				path = self.convertFilePathToUnicode(url.path())
				self.controller.openFile(path)

			event.acceptProposedAction()
		else:
			super(PrusaControllView, self).dropEvent(event)

	def convertFilePathToUnicode(self, path):
		codec = QtCore.QTextCodec.codecForName("UTF-16")
		convertedPath = unicode(codec.fromUnicode(path), 'UTF-16')
		return convertedPath

	def updateScene(self, reset=False):
		self.prusaControllWidget.updateScene(reset)


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

		self.selectButton.clicked.connect(self.controller.selectButtonPressed)
		self.moveButton.clicked.connect(self.controller.moveButtonPressed)
		self.rotateButton.clicked.connect(self.controller.rotateButtonPressed)
		self.scaleButton.clicked.connect(self.controller.scaleButtonPressed)

		self.toolTabVLayout = QtGui.QVBoxLayout()
		self.toolTabVLayout.addWidget(self.selectButton)
		self.toolTabVLayout.addWidget(self.moveButton)
		self.toolTabVLayout.addWidget(self.rotateButton)
		self.toolTabVLayout.addWidget(self.scaleButton)
		self.toolTabVLayout.addItem(QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))

		self.toolTab.setLayout(self.toolTabVLayout)
		#tool tab

		#print tab
		#TODO: Vytvorit print_settings.json ve kterem bude strom nastaveni pro ruzne materialy...
		#a bude se tady aplikovat jako vyjimky
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
		self.tabWidget.setCurrentIndex(1)
		self.tabWidget.setMaximumWidth(250)

		mainLayout = QtGui.QHBoxLayout()
		mainLayout.addWidget(self.glWidget)
		mainLayout.addWidget(self.tabWidget)

		self.setLayout(mainLayout)

		self.show()

	def updateScene(self, reset=False):
		self.glWidget.updateScene(reset)

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

