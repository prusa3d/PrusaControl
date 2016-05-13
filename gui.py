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
        self.language_label = QtGui.QLabel(self.tr("Language"))
        self.language_combo = QtGui.QComboBox()
        #set enumeration
        self.language_combo.addItems(self.controller.enumeration['language'].values())
        self.language_combo.setCurrentIndex(self.controller.enumeration['language'].keys().index(self.controller.settings['language']))

        self.printer_label = QtGui.QLabel(self.tr("Printer model"))
        self.printer_combo = QtGui.QComboBox()
        self.printer_combo.addItems(self.controller.enumeration['printer'].values())
        self.printer_combo.setCurrentIndex(self.controller.enumeration['printer'].keys().index(self.controller.settings['printer']))

        self.debug_checkbox = QtGui.QCheckBox(self.tr("Debug"))
        self.debug_checkbox.setChecked(self.controller.settings['debug'])

        self.automatic_placing_checkbox = QtGui.QCheckBox(self.tr("Automatic placing"))
        self.automatic_placing_checkbox.setChecked(self.controller.settings['automatic_placing'])

        layout.addWidget(self.language_label)
        layout.addWidget(self.language_combo)

        layout.addWidget(self.printer_label)
        layout.addWidget(self.printer_combo)

        layout.addWidget(self.debug_checkbox)
        layout.addWidget(self.automatic_placing_checkbox)

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
        data['language'] = controller.enumeration['language'].keys()[dialog.language_combo.currentIndex()]
        data['printer'] = controller.enumeration['printer'].keys()[dialog.printer_combo.currentIndex()]
        controller.set_printer(data['printer'])
        data['debug'] = dialog.debug_checkbox.isChecked()
        data['automatic_placing'] = dialog.automatic_placing_checkbox.isChecked()
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

        self.open_file_button = QtGui.QPushButton(self.tr("Open file"))

        self.update_button = QtGui.QPushButton(self.tr("Update"))
        #TODO:Doplnit
        #self.updateButton.clicked.connect(self.controller.updateFirmware)
        #self.updateButton.setEnabled(self.differentVersion)

        #layout.addWidget(self.actualVersionLabel)
        #layout.addWidget(self.yourVersionLabel)
        layout.addWidget(self.open_file_button)
        layout.addWidget(self.update_button)

        # Close button
        buttons = QDialogButtonBox(
            QDialogButtonBox.Close,
            Qt.Horizontal, self)
        buttons.clicked.connect(self.close)
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
        self.different_version = True
        self.actual_version = '1.0.2'
        self.your_version = '1.0.1'

        layout = QVBoxLayout(self)

        self.prusa_control_label = QtGui.QLabel("PrusaControl")
        self.prusa_control_label.setAlignment(Qt.AlignCenter)

        self.prusa_control_text = QtGui.QLabel("Created by Tibor Vavra for Prusa Research s.r.o.")

        self.local_version_label = QtGui.QLabel("Your version is %s" % self.your_version)

        self.check_version_button = QtGui.QPushButton(self.tr("Check version"))
        #TODO:Doplnit
        #self.checkVersionButton.clicked.connect(self.controller.checkVersion)
        #self.checkVersionButton.setEnabled(self.differentVersion)

        layout.addWidget(self.prusa_control_label)
        layout.addWidget(self.prusa_control_text)

        layout.addWidget(self.local_version_label)
        layout.addWidget(self.check_version_button)

        # Close button
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok,
            Qt.Horizontal, self)
        buttons.clicked.connect(self.close)
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
        self.printer_name = self.controller.get_printer_name()
        self.your_firmware_version = self.controller.get_firmware_version_number()

        layout = QVBoxLayout(self)

        self.printerNameLabel = QtGui.QLabel(self.tr("Your printer is") + " %s" % self.printer_name)

        self.printerFirmwareText = QtGui.QLabel(self.tr("Version of firmware is") + " %s" % self.your_firmware_version)


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


class PrusaControlView(QtGui.QMainWindow):
    def __init__(self, c):
        self.controller = c
        super(PrusaControlView, self).__init__()
        self.setAcceptDrops(True)

        self.prusa_control_widget = PrusaControlWidget(self)
        self.setCentralWidget(self.prusa_control_widget)

        self.menubar = self.menuBar()
        #file menu definition
        self.file_menu = self.menubar.addMenu(self.tr('&File'))
        self.file_menu.addAction(self.tr('Open project'), self.controller.open_project_file)
        self.file_menu.addAction(self.tr('Save project'), self.controller.save_project_file)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.tr('Import stl file'), self.controller.open_model_file)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.tr('Reset'), self.controller.reset_scene)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.tr('Close'), self.controller.close)
        #file menu definition

        #printer menu
        self.printer_menu = self.menubar.addMenu(self.tr('&Printer'))
        self.printer_menu.addAction(self.tr('Printer info'), self.controller.open_printer_info)
        self.printer_menu.addAction(self.tr('Update firmware'), self.controller.open_update_firmware)
        #printer menu

        #Settings menu
        self.settings_menu = self.menubar.addMenu(self.tr('&Settings'))
        self.settings_menu.addAction(self.tr('PrusaControl settings'), self.controller.open_settings)
        #Settings menu

        #Help menu
        self.help_menu = self.menubar.addMenu(self.tr('&Help'))
        self.help_menu.addAction('Help', self.controller.open_help)
        self.help_menu.addAction(self.tr('Prusa Online'), self.controller.open_shop)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.tr('About'), self.controller.open_about)
        #Help menu

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

    def open_project_file_dialog(self):
        filters = "Prus (*.prus *.PRUS)"
        title = 'Open project file'
        open_at = "/home"
        data = QtGui.QFileDialog.getOpenFileName(None, title, open_at, filters)
        data = self.convert_file_path_to_unicode(data)
        return data

    def open_model_file_dialog(self):
        filters = "STL (*.stl *.STL)"
        title = "Import stl file"
        open_at = "/home"
        data = QtGui.QFileDialog.getOpenFileName(None, title, open_at, filters)
        data = self.convert_file_path_to_unicode(data)
        return data

    def save_project_file_dialog(self):
        filters = "Prus (*.prus *.PRUS)"
        title = 'Save project file'
        open_at = "/home"
        data = QtGui.QFileDialog.getSaveFileName(None, title, open_at, filters)
        data = self.convert_file_path_to_unicode(data)
        if not data[-4:] == projectFile.fileExtension:
            data = data + '.' + projectFile.fileExtension

        return data

    def save_gcode_file_dialog(self):
        filters = "gcode (*.gcode *.GCODE)"
        title = 'Save G-Code file'
        open_at = "/home"
        data = QtGui.QFileDialog.getSaveFileName(None, title, open_at, filters)
        data = self.convert_file_path_to_unicode(data)
        return data

    def update_gui(self):
        self.prusa_control_widget.update_gui()

    #TODO:Move to controller class
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super(PrusaControlView, self).dragEnterEvent(event)

    def dragMoveEvent(self, event):
        super(PrusaControlView, self).dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                self.statusBar().showMessage('Dropped file name is ' + str(url.path()))
                path = self.convert_file_path_to_unicode(url.path())
                self.controller.open_file(path)

            event.acceptProposedAction()
        else:
            super(PrusaControlView, self).dropEvent(event)

    def convert_file_path_to_unicode(self, path):
        codec = QtCore.QTextCodec.codecForName("UTF-16")
        converted_path = unicode(codec.fromUnicode(path), 'UTF-16')
        return converted_path

    def update_scene(self, reset=False):
        self.prusa_control_widget.update_scene(reset)

    def set_zoom(self, diff):
        self.prusa_control_widget.set_zoom(diff)

    def get_zoom(self):
        return self.prusa_control_widget.get_zoom()

    def get_cursor_position(self, event):
        return self.prusa_control_widget.get_cursor_position(event)

    def get_cursor_pixel_color(self, event):
        return self.prusa_control_widget.get_cursor_pixel_color(event)

    def set_x_rotation(self, angle):
        self.prusa_control_widget.set_x_rotation(angle)

    def set_z_rotation(self, angle):
        self.prusa_control_widget.set_z_rotation(angle)

    def get_x_rotation(self):
        return self.prusa_control_widget.get_x_rotation()

    def get_z_rotation(self):
        return self.prusa_control_widget.get_z_rotation()

    def get_tool_buttons(self):
        return self.prusa_control_widget.get_tool_buttons()

    def clear_tool_buttons(self):
        self.prusa_control_widget.clear_tool_buttons()

    def set_progress_bar(self, value):
        self.prusa_control_widget.progressBar.setValue(value)

    def set_save_gcode_button(self):
        self.prusa_control_widget.generateButton.setText(self.tr("Save G-Code"))

    def set_cancel_button(self):
        self.prusa_control_widget.generateButton.setText(self.tr("Cancel"))

    def set_generate_button(self):
        self.prusa_control_widget.generateButton.setText(self.tr("Generate"))

    def set_print_info_text(self, string):
        self.prusa_control_widget.printing_filament_data.setText(string)

    def get_actual_printing_data(self):
        return self.prusa_control_widget.get_actual_printing_data()


class PrusaControlWidget(QtGui.QWidget):
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

        self.rightPanel = QtGui.QWidget()

        self.printTab = QtGui.QWidget()

        #print tab
        self.materialLabel = QtGui.QLabel(self.tr("Material"))
        self.materialCombo = QtGui.QComboBox()
        printing_materials_ls = self.controller.get_printing_materials()
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
        self.printingInfoLabel = QtGui.QLabel(self.tr("Print info:"))

        self.printing_filament_label = QtGui.QLabel(self.tr("Filament required:"))
        self.printing_filament_data = QtGui.QLabel('')

        #send feedback button
        self.send_feedback_button = QtGui.QPushButton(self.tr("Send feedback"))
        self.send_feedback_button.clicked.connect(self.controller.send_feedback)

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
        self.printTabVLayout.addWidget(self.printing_filament_label)
        self.printTabVLayout.addWidget(self.printing_filament_data)
        self.printTabVLayout.addItem(QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))
        self.printTabVLayout.addWidget(self.send_feedback_button)

        self.printTab.setLayout(self.printTabVLayout)
        self.printTab.setMaximumWidth(250)

        mainLayout = QtGui.QHBoxLayout()
        mainLayout.addWidget(self.glWidget)
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

        #material_label = self.materialCombo.currentText()
        material_index = self.materialCombo.currentIndex()

        material_printing_settings = self.controller.get_printing_settings_for_material(material_index)

        #update print quality widget
        self.qualityCombo.clear()
        material_printing_settings_quality_ls = self.controller.get_printing_material_quality(material_index)
        self.qualityCombo.addItems(material_printing_settings_quality_ls)

        #infill slider
        self.infillSlider.setValue(material_printing_settings['infill'])
        self.infillSlider.setMinimum(material_printing_settings['infillRange'][0])
        self.infillSlider.setMaximum(material_printing_settings['infillRange'][1])

    def get_actual_printing_data(self):
        material_index = self.materialCombo.currentIndex()
        quality_index = self.qualityCombo.currentIndex()
        infill_value = self.infillSlider.value()
        brim = self.brimCheckBox.isChecked()
        support = self.supportCheckBox.isChecked()

        data = {'material': material_index,
                'quality': quality_index,
                'infill': infill_value,
                'brim': brim,
                'support': support}
        return data

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

