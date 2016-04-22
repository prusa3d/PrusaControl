# -*- coding: utf-8 -*-
import logging
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

import projectFile
import sceneRender

class SettingsDialog(QDialog):
    def __init__(self, controller, parent = None):
        super(SettingsDialog, self).__init__(parent)

        self.controller = controller

        layout = QVBoxLayout(self)

        # nice widget for editing the date
        self.languageLabel = QtGui.QLabel(self.tr("Language"))
        self.languageCombo = QtGui.QComboBox()
        #set enumeration
        self.languageCombo.addItems(self.controller.enumeration['language'].values())
        self.languageCombo.setCurrentIndex(self.controller.enumeration['language'].keys().index(self.controller.settings['language']))

        self.printerLabel = QtGui.QLabel(self.tr("Printer model"))
        self.printerCombo = QtGui.QComboBox()
        self.printerCombo.addItems(self.controller.enumeration['printer'].values())
        self.printerCombo.setCurrentIndex(self.controller.enumeration['printer'].keys().index(self.controller.settings['printer']))

        self.debugCheckBox = QtGui.QCheckBox(self.tr("Debug"))
        self.debugCheckBox.setChecked(self.controller.settings['debug'])

        self.automaticPlacingCheckBox = QtGui.QCheckBox(self.tr("Automatic placing"))
        self.automaticPlacingCheckBox.setChecked(self.controller.settings['automatic_placing'])

        layout.addWidget(self.languageLabel)
        layout.addWidget(self.languageCombo)

        layout.addWidget(self.printerLabel)
        layout.addWidget(self.printerCombo)

        layout.addWidget(self.debugCheckBox)
        layout.addWidget(self.automaticPlacingCheckBox)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def get_settings_data(controller, parent = None):
        data = controller.settings
        dialog = SettingsDialog(controller, parent)
        dialog.setWindowTitle("Settings")
        result = dialog.exec_()
        data['language'] = controller.enumeration['language'].keys()[dialog.languageCombo.currentIndex()]
        data['printer'] = controller.enumeration['printer'].keys()[dialog.printerCombo.currentIndex()]
        data['debug'] = dialog.debugCheckBox.isChecked()
        data['automatic_placing'] = dialog.automaticPlacingCheckBox.isChecked()
        return (data, result == QDialog.Accepted)

class FirmwareUpdateDialog(QDialog):
    def __init__(self, controller, parent = None):
        super(FirmwareUpdateDialog, self).__init__(parent)

        self.controller = controller
        #self.differentVersion = True
        #self.actualVersion = '1.0.2'
        #self.yourVersion = '1.0.1'

        layout = QVBoxLayout(self)


        #self.actualVersionLabel = QtGui.QLabel("Actual version of firmware is %s" % self.actualVersion)
        #self.yourVersionLabel = QtGui.QLabel("Your version of firmware is %s" % self.yourVersion)

        self.openFileButton = QtGui.QPushButton(self.tr("Open file"))

        self.updateButton = QtGui.QPushButton(self.tr("Update"))
        #TODO:Doplnit
        #self.updateButton.clicked.connect(self.controller.updateFirmware)
        #self.updateButton.setEnabled(self.differentVersion)

        #layout.addWidget(self.actualVersionLabel)
        #layout.addWidget(self.yourVersionLabel)
        layout.addWidget(self.openFileButton)
        layout.addWidget(self.updateButton)

        # Close button
        buttons = QDialogButtonBox(
            QDialogButtonBox.Close,
            Qt.Horizontal, self)
        buttons.clicked.connect(self.close)
        #buttons.accepted.connect(self.accept)
        #buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def get_firmware_update(controller, parent = None):
        dialog = FirmwareUpdateDialog(controller, parent)
        dialog.setWindowTitle("Firmware update")
        result = dialog.exec_()
        data = {'msg': 'Update is complete. New version is ....'}
        return (data, result == QDialog.Accepted)


class AboutDialog(QDialog):
    def __init__(self, controller, parent = None):
        super(AboutDialog, self).__init__(parent)

        self.controller = controller
        self.differentVersion = True
        self.actualVersion = '1.0.2'
        self.yourVersion = '1.0.1'

        layout = QVBoxLayout(self)

        self.prusaControllLabel = QtGui.QLabel("PrusaControl")
        self.prusaControllLabel.setAlignment(Qt.AlignCenter)

        self.prusaControllText = QtGui.QLabel("Created by Tibor Vavra for Prusa Research s.r.o.")

        self.localVersionLabel = QtGui.QLabel("Your version is %s" % self.yourVersion)

        self.checkVersionButton = QtGui.QPushButton(self.tr("Check version"))
        #TODO:Doplnit
        #self.checkVersionButton.clicked.connect(self.controller.checkVersion)
        #self.checkVersionButton.setEnabled(self.differentVersion)

        layout.addWidget(self.prusaControllLabel)
        layout.addWidget(self.prusaControllText)

        layout.addWidget(self.localVersionLabel)
        layout.addWidget(self.checkVersionButton)

        # Close button
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok,
            Qt.Horizontal, self)
        buttons.clicked.connect(self.close)
        #buttons.accepted.connect(self.accept)
        #buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def get_about_dialog(controller, parent = None):
        dialog = AboutDialog(controller, parent)
        dialog.setWindowTitle("About")
        result = dialog.exec_()
        data = {'msg':'Update is complete. New version is ....'}
        return (data, result == QDialog.Accepted)


class PrinterInfoDialog(QDialog):
    def __init__(self, controller, parent= None):
        super(PrinterInfoDialog, self).__init__(parent)

        self.controller = controller
        self.printerName = self.controller.get_printer_name()
        self.yourFirmwareVersion = self.controller.get_firmware_version_number()

        layout = QVBoxLayout(self)

        self.printerNameLabel = QtGui.QLabel(self.tr("Your printer is") + " %s" % self.printerName)

        self.printerFirmwareText = QtGui.QLabel(self.tr("Version of firmware is") + " %s" % self.yourFirmwareVersion)


        #TODO:Doplnit
        #self.checkVersionButton.clicked.connect(self.controller.checkVersion)
        #self.checkVersionButton.setEnabled(self.differentVersion)

        layout.addWidget(self.printerNameLabel)
        layout.addWidget(self.printerFirmwareText)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok,
            Qt.Horizontal, self)
        buttons.clicked.connect(self.close)
        layout.addWidget(buttons)

    @staticmethod
    def get_printer_info_dialog(controller, parent = None):
        dialog = PrinterInfoDialog(controller, parent)
        dialog.setWindowTitle("Printer info")
        result = dialog.exec_()
        data = {'msg': 'Update is complete. New version is ....'}
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
        self.fileMenu = self.menubar.addMenu(self.tr('&File'))
        self.fileMenu.addAction(self.tr('Open project'), self.controller.open_project_file)
        self.fileMenu.addAction(self.tr('Save project'), self.controller.save_project_file)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.tr('Import stl file'), self.controller.open_model_file)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.tr('Reset'), self.controller.reset_scene)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.tr('Close'), self.controller.close)
        #file menu definition

        #printer menu
        self.printer_menu = self.menubar.addMenu(self.tr('&Printer'))
        self.printer_menu.addAction(self.tr('Printer info'), self.controller.open_printer_info)
        self.printer_menu.addAction(self.tr('Update firmware'), self.controller.open_update_firmware)
        #printer menu

        #Settings menu
        self.settingsMenu = self.menubar.addMenu(self.tr('&Settings'))
        self.settingsMenu.addAction(self.tr('PrusaControl settings'), self.controller.open_settings)
        #Settings menu

        #Help menu
        self.helpMenu = self.menubar.addMenu(self.tr('&Help'))
        self.helpMenu.addAction('Help')
        self.helpMenu.addAction(self.tr('Prusa Online'))
        self.helpMenu.addSeparator()
        self.helpMenu.addAction(self.tr('About'), self.controller.open_about)

        #Help menu

        #status bar widgets
        '''
        self.progress_bar = QtGui.QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setTextVisible(False)
        self.cancel_button = QtGui.QPushButton("X")
        self.cancel_button.setMaximumWidth(20)
        self.progress_bar.setMaximumWidth(100)
        self.statusLabel = QtGui.QLabel(self)
        self.statusBar().addPermanentWidget(self.statusLabel)
        self.statusBar().addPermanentWidget(self.progress_bar, 0)
        self.statusBar().addPermanentWidget(self.cancel_button, 0)
        self.progress_bar.setValue(0)
        '''
        #status bar widgets

        self.statusBar().showMessage('Ready')
        self.setWindowTitle(self.tr("PrusaControl"))
        self.show()

    def open_settings_dialog(self):
        data, ok = SettingsDialog.get_settings_data(self.controller, self.parent())
        return data

    def open_printer_info_dialog(self):
        PrinterInfoDialog.get_printer_info_dialog(self.controller, self.parent())

    def open_about_dialog(self):
        AboutDialog.get_about_dialog(self.controller, self.parent())

    def open_firmware_dialog(self):
        data, ok = FirmwareUpdateDialog.get_firmware_update(self.controller, self.parent())

    def disable_save_gcode_button(self):
        self.prusaControllWidget.disable_save_gcode_button()

    def enable_save_gcode_button(self):
        self.prusaControllWidget.enable_save_gcode_button()

    def open_project_file_dialog(self):
        filters = "Prus (*.prus *.PRUS)"
        title = 'Open project file'
        openAt = "/home"
        data = QtGui.QFileDialog.getOpenFileName(None, title, openAt, filters)
        data = self.convert_file_path_to_unicode(data)
        return data

    def open_model_file_dialog(self):
        filters = "STL (*.stl *.STL)"
        title = "Import stl file"
        openAt = "/home"
        data = QtGui.QFileDialog.getOpenFileName(None, title, openAt, filters)
        data = self.convert_file_path_to_unicode(data)
        return data

    def save_project_file_dialog(self):
        filters = "Prus (*.prus *.PRUS)"
        title = 'Save project file'
        openAt = "/home"
        data = QtGui.QFileDialog.getSaveFileName(None, title, openAt, filters)
        data = self.convert_file_path_to_unicode(data)
        if not data[-4:] == projectFile.fileExtension:
            data = data + '.' + projectFile.fileExtension

        return data

    def save_gcode_file_dialog(self):
        filters = "gcode (*.gcode *.GCODE)"
        title = 'Save G-Code file'
        openAt = "/home"
        data = QtGui.QFileDialog.getSaveFileName(None, title, openAt, filters)
        data = self.convert_file_path_to_unicode(data)
        return data

    def update_gui(self):
        self.prusaControllWidget.update_gui()

    #TODO:Move to controller class
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
                path = self.convert_file_path_to_unicode(url.path())
                self.controller.open_file(path)

            event.acceptProposedAction()
        else:
            super(PrusaControllView, self).dropEvent(event)

    def convert_file_path_to_unicode(self, path):
        codec = QtCore.QTextCodec.codecForName("UTF-16")
        converted_path = unicode(codec.fromUnicode(path), 'UTF-16')
        return converted_path

    def update_scene(self, reset=False):
        self.prusaControllWidget.update_scene(reset)

    def set_zoom(self, diff):
        self.prusaControllWidget.set_zoom(diff)

    def get_zoom(self):
        return self.prusaControllWidget.get_zoom()

    def get_cursor_position(self, event):
        return self.prusaControllWidget.get_cursor_position(event)

    def get_cursor_pixel_color(self, event):
        return self.prusaControllWidget.get_cursor_pixel_color(event)

    def set_x_rotation(self, angle):
        self.prusaControllWidget.set_x_rotation(angle)

    def set_z_rotation(self, angle):
        self.prusaControllWidget.set_z_rotation(angle)

    def get_x_rotation(self):
        return self.prusaControllWidget.get_x_rotation()

    def get_z_rotation(self):
        return self.prusaControllWidget.get_z_rotation()

    def get_tool_buttons(self):
        return self.prusaControllWidget.get_tool_buttons()

    def clear_tool_buttons(self):
        self.prusaControllWidget.clear_tool_buttons()

    def set_progress_bar(self, value):
        self.prusaControllWidget.progressBar.setValue(value)


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

        self.init_gui()

    def init_gui(self):
        self.glWidget = sceneRender.GLWidget(self)

        self.tabWidget = QtGui.QTabWidget()
        self.rightPanel = QtGui.QWidget()

        #self.toolTab = QtGui.QWidget()
        self.printTab = QtGui.QWidget()

        #tool tab
        '''
        self.moveButton = QtGui.QPushButton("Move")
        self.rotateButton = QtGui.QPushButton("Rotate")
        self.scaleButton = QtGui.QPushButton("Scale")

        self.toolButtonGroup = QtGui.QButtonGroup()
        self.toolButtonGroup.setExclusive(True)

        self.toolButtonGroup.addButton(self.moveButton)
        self.toolButtonGroup.addButton(self.rotateButton)
        self.toolButtonGroup.addButton(self.scaleButton)

        self.moveButton.setCheckable(True)
        self.rotateButton.setCheckable(True)
        self.scaleButton.setCheckable(True)

        self.moveButton.clicked.connect(self.controller.moveButtonPressed)
        self.rotateButton.clicked.connect(self.controller.rotateButtonPressed)
        self.scaleButton.clicked.connect(self.controller.scaleButtonPressed)

        self.toolTabVLayout = QtGui.QVBoxLayout()
        self.toolTabVLayout.addWidget(self.moveButton)
        self.toolTabVLayout.addWidget(self.rotateButton)
        self.toolTabVLayout.addWidget(self.scaleButton)
        self.toolTabVLayout.addItem(QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))

        self.toolTab.setLayout(self.toolTabVLayout)
        '''
        #tool tab

        #print tab
        self.materialLabel = QtGui.QLabel(self.tr("Material"))
        self.materialCombo = QtGui.QComboBox()
        printing_materials_ls = [self.controller.get_enumeration('materials', i) for i in self.controller.get_printing_materials()]
        self.materialCombo.addItems(printing_materials_ls)
        self.materialCombo.currentIndexChanged.connect(self.controller.update_gui)

        self.qualityLabel = QtGui.QLabel(self.tr("Quality"))
        self.qualityCombo = QtGui.QComboBox()

        self.infillLabel = QtGui.QLabel(self.tr("Infill") + " %s" % str(self.infillValue)+'%')
        self.infillSlider = self.create_slider(self.set_infill, self.infillValue)

        self.supportCheckBox = QtGui.QCheckBox(self.tr("Support material"))
        self.brimCheckBox = QtGui.QCheckBox(self.tr("Brim"))

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)

        self.generateButton = QtGui.QPushButton(self.tr("Generate"))
        self.generateButton.clicked.connect(self.controller.generate_button_pressed)

        #printing info place
        self.printingInfoLabel = QtGui.QLabel("Print info:")

        self.saveGCodeButton = QtGui.QPushButton(self.tr("Save G-Code"))
        self.saveGCodeButton.clicked.connect(self.controller.save_gcode_file)

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

        #self.tabWidget.addTab(self.toolTab, "Tools")
        #self.tabWidget.addTab(self.printTab, "Print")
        #self.tabWidget.setCurrentIndex(1)
        #self.tabWidget.setMaximumWidth(250)
        #self.tabWidget.connect(self.tabWidget, QtCore.SIGNAL("currentChanged(int)"), self.controller.tab_selected)

        self.printTab.setMaximumWidth(250)

        mainLayout = QtGui.QHBoxLayout()
        mainLayout.addWidget(self.glWidget)
        #mainLayout.addWidget(self.tabWidget)


        mainLayout.addWidget(self.printTab)

        self.setLayout(mainLayout)
        self.update_gui_for_material()

        self.show()

    def update_gui(self):
        self.update_gui_for_material()

    def update_gui_for_material(self, set_materials=0):
        if set_materials:
            self.materialCombo.clear()
            printing_materials_ls = [self.controller.get_enumeration('materials', i) for i in self.controller.get_printing_materials()]
            self.materialCombo.addItems(printing_materials_ls)

        material = self.materialCombo.currentIndex()
        material_printing_settings = self.controller.get_printing_settings_for_material(material)

        #update print quality widget
        self.qualityCombo.clear()
        material_printing_settings_quality_ls = [self.controller.get_enumeration('quality', i) for i in material_printing_settings['quality']]
        self.qualityCombo.addItems(material_printing_settings_quality_ls)

        #infill slider
        self.infillSlider.setValue(material_printing_settings['infill'])
        self.infillSlider.setMinimum(material_printing_settings['infillRange'][0])
        self.infillSlider.setMaximum(material_printing_settings['infillRange'][1])

    def clear_tool_buttons(self):
        self.toolButtonGroup.setExclusive(False)
        self.moveButton.setChecked(False)
        self.rotateButton.setChecked(False)
        self.scaleButton.setChecked(False)
        self.toolButtonGroup.setExclusive(True)

    def set_x_rotation(self, angle):
        self.glWidget.set_x_rotation(angle)

    def set_z_rotation(self, angle):
        self.glWidget.set_z_rotation(angle)

    def get_x_rotation(self):
        return self.glWidget.xRot

    def get_z_rotation(self):
        return self.glWidget.zRot

    def get_zoom(self):
        return self.glWidget.get_zoom()

    def set_zoom(self, diff):
        self.glWidget.set_zoom(diff)

    def get_cursor_position(self, event):
        return self.glWidget.get_cursor_position(event)

    def get_cursor_pixel_color(self, event):
        return self.glWidget.get_cursor_pixel_color(event)

    def get_tool_buttons(self):
        return [self.glWidget.moveTool, self.glWidget.rotateTool, self.glWidget.scaleTool]

    def update_scene(self, reset=False):
        self.glWidget.update_scene(reset)

    def disable_save_gcode_button(self):
        self.saveGCodeButton.setDisabled(True)

    def enable_save_gcode_button(self):
        self.saveGCodeButton.setDisabled(False)

    def set_infill(self, val):
        self.infillValue = val
        self.infillLabel.setText(self.tr("Infill") + " " + str(val) + "%")

    def create_slider(self, setterSlot, defaultValue=0, rangeMin=0, rangeMax=100):
        slider = QtGui.QSlider(QtCore.Qt.Horizontal)

        slider.setRange(rangeMin, rangeMax)
        slider.setSingleStep(10)
        slider.setPageStep(20)
        slider.setTickInterval(10)
        slider.setValue(defaultValue)
        slider.setTickPosition(QtGui.QSlider.TicksRight)

        self.connect(slider, QtCore.SIGNAL("valueChanged(int)"), setterSlot)
        return slider

