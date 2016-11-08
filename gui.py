# -*- coding: utf-8 -*-
import logging
import math
import os

import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt4 import *
from PyQt4 import QtGui

from PyQt4.QtCore import QDateTime, Qt
from PyQt4.QtGui import QDialog, QDateTimeEdit, QDialogButtonBox
from PyQt4.QtGui import *
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
        self.printer_combo.addItems(self.controller.get_printers_labels_ls())
        self.printer_combo.setCurrentIndex(self.controller.get_printers_names_ls().index(self.controller.settings['printer']))

        self.printer_type_label = QtGui.QLabel(self.tr("Printer variation"))
        self.printer_type_combo = QtGui.QComboBox()
        self.printer_type_combo.addItems(self.controller.get_printer_variations_labels_ls(self.controller.actual_printer))
        self.printer_type_combo.setCurrentIndex(self.controller.get_printer_variations_names_ls(self.controller.actual_printer).index(self.controller.settings['printer_type']))

        self.debug_checkbox = QtGui.QCheckBox(self.tr("Debug"))
        self.debug_checkbox.setChecked(self.controller.settings['debug'])

        self.automatic_placing_checkbox = QtGui.QCheckBox(self.tr("Automatic placing"))
        self.automatic_placing_checkbox.setChecked(self.controller.settings['automatic_placing'])

        self.analyze_checkbox = QtGui.QCheckBox(self.tr("Analyzer"))
        self.analyze_checkbox .setChecked(self.controller.settings['analyze'])

        self.update_parameters_checkbox = QtGui.QCheckBox(self.tr("Auto update parameters"))
        self.update_parameters_checkbox.setChecked(self.controller.settings['automatic_update_parameters'])

        layout.addWidget(self.language_label)
        layout.addWidget(self.language_combo)

        layout.addWidget(self.printer_label)
        layout.addWidget(self.printer_combo)

        layout.addWidget(self.printer_type_label)
        layout.addWidget(self.printer_type_combo)

        layout.addWidget(self.debug_checkbox)
        layout.addWidget(self.automatic_placing_checkbox)
        layout.addWidget(self.analyze_checkbox)
        layout.addWidget(self.update_parameters_checkbox)

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
        data['printer'] = controller.get_printers_names_ls()[dialog.printer_combo.currentIndex()]
        data['printer_type'] = controller.get_printer_variations_names_ls(data['printer'])[dialog.printer_type_combo.currentIndex()]
        controller.set_printer(data['printer'])
        data['debug'] = dialog.debug_checkbox.isChecked()
        data['automatic_placing'] = dialog.automatic_placing_checkbox.isChecked()
        data['analyze'] = dialog.analyze_checkbox.isChecked()
        data['automatic_update_parameters'] = dialog.update_parameters_checkbox.isChecked()
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
        #self.actual_version = '1.0.2'
        self.your_version = self.controller.app_config.version

        layout = QVBoxLayout(self)

        self.prusa_control_label = QtGui.QLabel("PrusaControl")
        self.prusa_control_label.setAlignment(Qt.AlignCenter)

        self.prusa_control_text = QtGui.QLabel("Created by Tibor Vavra for Prusa Research s.r.o.")

        self.local_version_label = QtGui.QLabel("Your version is %s" % self.your_version)

        #self.check_version_button = QtGui.QPushButton(self.tr("Check version"))
        #TODO:Doplnit
        #self.checkVersionButton.clicked.connect(self.controller.checkVersion)
        #self.checkVersionButton.setEnabled(self.differentVersion)

        layout.addWidget(self.prusa_control_label)
        layout.addWidget(self.prusa_control_text)

        layout.addWidget(self.local_version_label)
        #layout.addWidget(self.check_version_button)

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

        self.is_setting_panel_opened = False
        #self.setStyleSheet()

        self.setObjectName('PrusaControlView')
        css = QtCore.QFile('data/my_stylesheet.css')
        css.open(QtCore.QIODevice.ReadOnly)
        if css.isOpen():
            self.setStyleSheet(QtCore.QVariant(css.readAll()).toString())
            css.close()

        self.infillValue = 20
        self.changable_widgets = {}

        self.object_id = 0

        self.setVisible(False)

        self.centralWidget = QtGui.QWidget()
        self.object_settings_panel = None


        self.menubar = self.menuBar()
        # file menu definition
        self.file_menu = self.menubar.addMenu(self.tr('&File'))
        self.file_menu.addAction(self.tr('Import model file'), self.controller.open_model_file)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.tr('Open project'), self.controller.open_project_file)
        self.file_menu.addAction(self.tr('Save project'), self.controller.save_project_file)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.tr('Reset'), self.controller.reset)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.tr('Close'), self.controller.close)
        # file menu definition

        # TODO:Uncoment after new function created/tested
        # printer menu
        # self.printer_menu = self.menubar.addMenu(self.tr('&Printer'))
        # self.printer_menu.addAction(self.tr('Printer info'), self.controller.open_printer_info)
        # self.printer_menu.addAction(self.tr('Update firmware'), self.controller.open_update_firmware)
        # printer menu

        # Settings menu
        self.settings_menu = self.menubar.addMenu(self.tr('&Settings'))
        self.settings_menu.addAction(self.tr('PrusaControl settings'), self.controller.open_settings)
        # Settings menu

        # Help menu
        self.help_menu = self.menubar.addMenu(self.tr('&Help'))
        self.help_menu.addAction('Help', self.controller.open_help)
        self.help_menu.addAction(self.tr('Prusa Online'), self.controller.open_shop)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.tr("Send feedback"), self.controller.send_feedback)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.tr('About'), self.controller.open_about)
        # Help menu

        #self.prusa_control_widget = PrusaControlWidget(self)

        self.glWidget = sceneRender.GLWidget(self)
        self.glWidget.setObjectName('glWidget')

        self.right_panel = QtGui.QWidget()
        self.right_panel.setObjectName('right_panel')
        self.right_panel_layout = QtGui.QHBoxLayout()
        self.right_panel_layout.setObjectName('right_panel_layout')


        self.printTab = QtGui.QWidget()
        # print tab
        self.materialLabel = QtGui.QLabel(self.tr("Material"))
        self.materialLabel.setObjectName('materialLabel')
        self.materialCombo = QtGui.QComboBox()
        self.materialCombo.setObjectName('materialCombo')
        material_label_ls, first = self.controller.get_printer_materials_labels_ls(self.controller.actual_printer)
        self.materialCombo.addItems(material_label_ls)
        self.materialCombo.setCurrentIndex(first)
        self.materialCombo.currentIndexChanged.connect(self.controller.update_gui)

        '''
        self.materialCombo.style().unpolish(self.materialCombo)
        self.materialCombo.style().polish(self.materialCombo)
        self.materialCombo.update()
        print("Style: " + str(self.materialCombo.styleSheet()))
        '''

        self.qualityLabel = QtGui.QLabel(self.tr("Quality"))
        self.qualityLabel.setObjectName('qualityLabel')
        self.qualityCombo = QtGui.QComboBox()
        self.qualityCombo.setObjectName('qualityCombo')

        self.infillLabel = QtGui.QLabel(self.tr("Infill") + " %s" % str(self.infillValue) + '%')
        self.infillLabel.setObjectName('infillLabel')
        self.infillSlider = self.create_slider(self.set_infill, self.infillValue)
        self.infillSlider.setObjectName('infillSlider')

        #self.supportCheckBox = QtGui.QCheckBox(self.tr("Support material"))
        self.supportLabel = QtGui.QLabel(self.tr("Support"))
        self.supportLabel.setObjectName('supportLabel')
        self.supportCombo = QtGui.QComboBox()
        self.supportCombo.addItems(["None", "Build plate only", "Everywhere"])
        self.supportCombo.setObjectName('supportCombo')

        self.brimCheckBox = QtGui.QCheckBox(self.tr("Brim"))
        self.brimCheckBox.setObjectName('brimCheckBox')

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setObjectName('progressBar')
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)

        self.generateButton = QtGui.QPushButton(self.tr("Generate"))
        self.generateButton.setObjectName('generateButton')
        self.generateButton.clicked.connect(self.controller.generate_button_pressed)
        self.generateButton.setEnabled(False)

        # printing info place
        self.printingInfoLabel = QtGui.QLabel(self.tr("Print info:"))
        self.printingInfoLabel.setObjectName('printingInfoLabel')

        self.printing_filament_label = QtGui.QLabel(self.tr("Filament required:"))
        self.printing_filament_label.setObjectName('printing_filament_label')
        self.printing_filament_data = QtGui.QLabel('')
        self.printing_filament_data.setObjectName('printing_filament_data')

        # send feedback button
        #self.send_feedback_button = QtGui.QPushButton(self.tr("Send feedback"))
        #self.send_feedback_button.clicked.connect(self.controller.send_feedback)

        self.printTabVLayout = QtGui.QVBoxLayout()
        self.printTabVLayout.setObjectName('printTabVLayout')

        self.printTabVLayout.addWidget(self.materialLabel)
        self.printTabVLayout.addWidget(self.materialCombo)
        self.printTabVLayout.addWidget(self.qualityLabel)
        self.printTabVLayout.addWidget(self.qualityCombo)
        self.printTabVLayout.addWidget(self.infillLabel)
        self.printTabVLayout.addWidget(self.infillSlider)
        #self.printTabVLayout.addWidget(self.supportCheckBox)
        self.printTabVLayout.addWidget(self.supportLabel)
        self.printTabVLayout.addWidget(self.supportCombo)
        self.printTabVLayout.addWidget(self.brimCheckBox)
        self.printTabVLayout.addWidget(self.progressBar)
        self.printTabVLayout.addWidget(self.generateButton)
        self.printTabVLayout.addWidget(self.printingInfoLabel)
        self.printTabVLayout.addWidget(self.printing_filament_label)
        self.printTabVLayout.addWidget(self.printing_filament_data)
        self.printTabVLayout.addItem(QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))
        #self.printTabVLayout.addWidget(self.send_feedback_button)

        #print("Style: " + str(self.materialCombo.styleSheet().toAscii()))


        self.printTab.setLayout(self.printTabVLayout)
        self.printTab.setMaximumWidth(250)


        self.right_panel_layout.addWidget(self.printTab)
        self.right_panel.setLayout(self.right_panel_layout)
        self.right_panel.setMaximumWidth(250)


        layout = QFormLayout(self)

        # TODO: nice widget for editing position
        self.object_settings_panel = QWidget()
        self.object_settings_panel.setVisible(False)

        layout.setAlignment(Qt.AlignLeft)

        menu_label = QtGui.QLabel(self.tr("Object settings"))
        self.filename_label = QtGui.QLabel("")
        position = QtGui.QLabel(self.tr("Position"))
        self.edit_pos_x = QtGui.QSpinBox()
        self.edit_pos_x.setMaximum(200)
        self.edit_pos_x.setMinimum(-200)
        self.edit_pos_x.setSuffix("mm")
        self.edit_pos_x.valueChanged.connect(lambda: self.set_position_on_object(self.edit_pos_x,
                                                                                 self.get_object_id(),
                                                                                 self.edit_pos_x.value(),
                                                                                 self.edit_pos_y.value(),
                                                                                 self.edit_pos_z.value(),
                                                                                 self.place_on_zero.isChecked()))

        self.edit_pos_y = QtGui.QSpinBox()
        self.edit_pos_y.setMaximum(200)
        self.edit_pos_y.setMinimum(-200)
        self.edit_pos_y.setSuffix("mm")
        self.edit_pos_y.valueChanged.connect(lambda: self.set_position_on_object(self.edit_pos_y,
                                                                                self.get_object_id(),
                                                                                self.edit_pos_x.value(),
                                                                                self.edit_pos_y.value(),
                                                                                self.edit_pos_z.value(),
                                                                                self.place_on_zero.isChecked()))

        self.edit_pos_z = QtGui.QSpinBox()
        self.edit_pos_z.setMaximum(300)
        self.edit_pos_z.setMinimum(-50)
        self.edit_pos_z.setSuffix("mm")
        self.edit_pos_z.valueChanged.connect(lambda: self.set_position_on_object(self.edit_pos_z,
                                                                                self.get_object_id(),
                                                                                self.edit_pos_x.value(),
                                                                                self.edit_pos_y.value(),
                                                                                self.edit_pos_z.value(),
                                                                                 self.place_on_zero.isChecked()))


        rotation = QtGui.QLabel(self.tr("Rotation"))
        self.edit_rot_x = QtGui.QSpinBox()
        self.edit_rot_x.setMaximum(360)
        self.edit_rot_x.setMinimum(-360)
        self.edit_rot_x.setSuffix(u"°")
        self.edit_rot_x.valueChanged.connect(lambda: self.set_rotation_on_object(self.edit_rot_x,
                                                                                self.get_object_id(),
                                                                                self.edit_rot_x.value(),
                                                                                self.edit_rot_y.value(),
                                                                                self.edit_rot_z.value(),
                                                                                self.place_on_zero.isChecked()))

        self.edit_rot_y = QtGui.QSpinBox()
        self.edit_rot_y.setMaximum(360)
        self.edit_rot_y.setMinimum(-360)
        self.edit_rot_y.setSuffix(u"°")
        self.edit_rot_y.valueChanged.connect(lambda: self.set_rotation_on_object(self.edit_rot_y,
                                                                                self.get_object_id(),
                                                                                self.edit_rot_x.value(),
                                                                                self.edit_rot_y.value(),
                                                                                self.edit_rot_z.value(),
                                                                                self.place_on_zero.isChecked()))

        self.edit_rot_z = QtGui.QSpinBox()
        self.edit_rot_z.setMaximum(360)
        self.edit_rot_z.setMinimum(-360)
        self.edit_rot_z.setSuffix(u"°")
        self.edit_rot_z.valueChanged.connect(lambda: self.set_rotation_on_object(self.edit_rot_z,
                                                                                self.get_object_id(),
                                                                                self.edit_rot_x.value(),
                                                                                self.edit_rot_y.value(),
                                                                                self.edit_rot_z.value(),
                                                                                self.place_on_zero.isChecked()))


        scale = QtGui.QLabel(self.tr("Scale"))
        self.edit_scale_x = QtGui.QDoubleSpinBox()
        self.edit_scale_x.setMaximum(9999)
        self.edit_scale_x.setMinimum(1)
        self.edit_scale_x.setSuffix("%")
        self.edit_scale_x.setDecimals(0)
        self.edit_scale_x.valueChanged.connect(lambda: self.set_scale_on_object(self.edit_scale_x,
                                                                                'x',
                                                                                self.get_object_id(),
                                                                                self.edit_scale_x.value(),
                                                                                self.edit_scale_y.value(),
                                                                                self.edit_scale_z.value(),
                                                                                self.place_on_zero.isChecked()))

        self.edit_scale_y = QtGui.QDoubleSpinBox()
        self.edit_scale_y.setMaximum(9999)
        self.edit_scale_y.setMinimum(1)
        self.edit_scale_y.setSuffix("%")
        self.edit_scale_y.setDecimals(0)
        self.edit_scale_y.valueChanged.connect(lambda: self.set_scale_on_object(self.edit_scale_y,
                                                                                'y',
                                                                                self.get_object_id(),
                                                                                self.edit_scale_x.value(),
                                                                                self.edit_scale_y.value(),
                                                                                self.edit_scale_z.value(),
                                                                                self.place_on_zero.isChecked()))

        self.edit_scale_z = QtGui.QDoubleSpinBox()
        self.edit_scale_z.setMaximum(9999)
        self.edit_scale_z.setMinimum(1)
        self.edit_scale_z.setSuffix("%")
        self.edit_scale_z.setDecimals(0)
        self.edit_scale_z.valueChanged.connect(lambda: self.set_scale_on_object(self.edit_scale_z,
                                                                                'z',
                                                                                self.get_object_id(),
                                                                                self.edit_scale_x.value(),
                                                                                self.edit_scale_y.value(),
                                                                                self.edit_scale_z.value(),
                                                                                self.place_on_zero.isChecked()))
        self.combobox_scale_units = QtGui.QComboBox()
        self.combobox_scale_units.addItems(["percent","mm"])
        self.combobox_scale_units.setCurrentIndex(0)
        self.scale_units = self.combobox_scale_units.currentText()
        self.combobox_scale_units.currentIndexChanged.connect(self.change_scale_units)
        self.lock_scale_axes_checkbox = QtGui.QCheckBox(self.tr("Lock axes"))
        self.lock_scale_axes_checkbox.stateChanged.connect(self.lock_scale_axes_change)
        self.lock_scale_axes_checkbox.setChecked(True)


        layout.addWidget(menu_label)
        layout.addWidget(self.filename_label)
        layout.addWidget(position)
        layout.addRow(QtGui.QLabel('X'), self.edit_pos_x)
        layout.addRow(QtGui.QLabel('Y'), self.edit_pos_y)
        layout.addRow(QtGui.QLabel('Z'), self.edit_pos_z)
        layout.addWidget(QtGui.QLabel(''))

        layout.addWidget(rotation)
        layout.addRow(QtGui.QLabel('X'), self.edit_rot_x)
        layout.addRow(QtGui.QLabel('Y'), self.edit_rot_y)
        layout.addRow(QtGui.QLabel('Z'), self.edit_rot_z)
        layout.addWidget(QtGui.QLabel(''))

        layout.addWidget(scale)
        layout.addRow(QtGui.QLabel('X'), self.edit_scale_x)
        layout.addRow(QtGui.QLabel('Y'), self.edit_scale_y)
        layout.addRow(QtGui.QLabel('Z'), self.edit_scale_z)
        layout.addRow(QtGui.QLabel('Units'), self.combobox_scale_units)
        layout.addWidget(self.lock_scale_axes_checkbox)
        layout.addWidget(QtGui.QLabel(''))





        self.place_on_zero = QtGui.QCheckBox(self.tr("Place on zero"))
        self.place_on_zero.setChecked(True)
        layout.addWidget(self.place_on_zero)
        layout.addWidget(QtGui.QLabel(''))

        #layout.addWidget(edit_pos_z)
        #layout.setSpacing(1)
        #layout.addSpacerItem(QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.apply_object_settings)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.cancel_object_settings)

        layout.addWidget(apply_button)
        layout.addWidget(cancel_button)

        self.object_settings_panel.setLayout(layout)
        self.object_settings_panel.setMaximumWidth(150)

        self.line = QFrame()
        self.line.setVisible(False)
        self.line.setFrameShape(QFrame.VLine)


        self.gcode_panel = QWidget()
        self.gcode_label = QLabel("0")
        self.gcode_label.setMaximumWidth(40)
        self.gcode_label.setAlignment(Qt.AlignCenter)

        self.gcode_slider = self.create_slider(self.set_gcode_slider, 0, 0, 100 ,QtCore.Qt.Vertical)
        #self.gcode_from_button_checkbox = QtGui.QCheckBox(self.tr("From button"))
        #self.gcode_from_button_checkbox.setChecked(True)
        #self.gcode_from_button_checkbox.clicked.connect(self.set_gcode_draw_layers_from_button)

        '''
        self.gcode_slider = QtGui.QSlider(QtCore.Qt.Vertical)
        self.gcode_slider.setRange(0, 100)
        self.gcode_slider.setMaximumWidth(20)
        self.gcode_slider.valueChanged.connect(self.controller.scene_was_changed)
        '''

        self.gcode_cancel_button = QPushButton('X')
        self.gcode_cancel_button.setMaximumWidth(40)
        self.gcode_cancel_button.clicked.connect(self.controller.set_model_edit_view)
        gcode_panel_layout = QVBoxLayout()
        gcode_panel_layout.setMargin(0)
        gcode_panel_layout.setSpacing(0)
        gcode_panel_layout.addWidget(self.gcode_label)
        gcode_panel_layout.addWidget(self.gcode_slider)
        #gcode_panel_layout.addWidget(self.gcode_from_button_checkbox)
        gcode_panel_layout.addWidget(self.gcode_cancel_button)
        self.gcode_panel.setLayout(gcode_panel_layout)
        self.gcode_panel.setVisible(False)



        self.right_panel_layout.insertWidget(0, self.object_settings_panel)
        self.right_panel_layout.insertWidget(1, self.gcode_panel)
        self.right_panel_layout.insertWidget(2, self.line)

        mainLayout = QtGui.QHBoxLayout()
        mainLayout.setSpacing(0)
        mainLayout.setMargin(0)
        mainLayout.addWidget(self.glWidget)
        mainLayout.addWidget(self.right_panel)

        self.centralWidget.setLayout(mainLayout)
        self.setCentralWidget(self.centralWidget)

        self.statusBar().showMessage('Ready')
        self.setWindowTitle(self.tr("PrusaControl " + self.controller.app_config.version))

        self.setVisible(True)
        #self.update_gui()

        self.changable_widgets['brimCheckBox'] = self.brimCheckBox
        #self.changable_widgets['supportCheckBox'] = self.supportCheckBox
        self.changable_widgets['supportCombo'] = self.supportCombo


        self.qualityCombo.currentIndexChanged.connect(self.controller.scene_was_changed)
        self.infillSlider.valueChanged.connect(self.controller.scene_was_changed)
        #self.supportCheckBox.clicked.connect(self.controller.scene_was_changed)
        self.supportCombo.currentIndexChanged.connect(self.controller.scene_was_changed)
        self.brimCheckBox.clicked.connect(self.controller.scene_was_changed)

        self.glWidget.setFocusPolicy(Qt.StrongFocus)

        self.show()

    def reinit(self):
        self.update_gui_for_material()

    def set_progress_bar(self, value):
        self.progressBar.setValue(value)

    def set_save_gcode_button(self):
        self.generateButton.setText(self.tr("Save G-Code"))

    def set_cancel_button(self):
        self.generateButton.setText(self.tr("Cancel"))

    def set_generate_button(self):
        self.generateButton.setText(self.tr("Generate"))

    def set_print_info_text(self, string):
        self.printing_filament_data.setText(string)

    def get_changable_widgets(self):
        return self.changable_widgets

    def get_object_id(self):
        return self.object_id

    def update_object_settings(self, object_id):
        if self.is_setting_panel_opened:
            self.set_gui_for_object(object_id)
        else:
            return

    def create_object_settings_menu(self, object_id):
        if self.is_setting_panel_opened:
            self.set_gui_for_object(object_id)
        else:
            mesh = self.controller.get_object_by_id(object_id)
            if not mesh:
                return
            self.right_panel.setMaximumWidth(400)
            self.object_settings_panel.setVisible(True)
            self.line.setVisible(True)
            self.set_gui_for_object(object_id)
            self.is_setting_panel_opened = True
        self.glWidget.setFocusPolicy(Qt.NoFocus)
        self.object_settings_panel.setFocusPolicy(Qt.StrongFocus)

    def set_gui_for_object(self, object_id, scale_units_perc=True):
        mesh = self.controller.get_object_by_id(object_id)
        if not mesh:
            return
        mesh.start_edit()
        self.object_id = object_id

        self.filename_label.setText(mesh.filename)
        self.edit_pos_x.setDisabled(True)
        self.edit_pos_x.setValue(mesh.pos[0]*10)
        self.edit_pos_x.setDisabled(False)

        self.edit_pos_y.setDisabled(True)
        self.edit_pos_y.setValue(mesh.pos[1]*10)
        self.edit_pos_y.setDisabled(False)

        self.edit_pos_z.setDisabled(True)
        self.edit_pos_z.setValue(mesh.pos[2]*10)
        self.edit_pos_z.setDisabled(False)

        self.edit_rot_x.setDisabled(True)
        self.edit_rot_x.setValue(np.rad2deg(mesh.rot[0]))
        self.edit_rot_x.setDisabled(False)

        self.edit_rot_y.setDisabled(True)
        self.edit_rot_y.setValue(np.rad2deg(mesh.rot[1]))
        self.edit_rot_y.setDisabled(False)

        self.edit_rot_z.setDisabled(True)
        self.edit_rot_z.setValue(np.rad2deg(mesh.rot[2]))
        self.edit_rot_z.setDisabled(False)

        self.set_scale_widgets(mesh)


    def set_scale_widgets(self, mesh):
        self.edit_scale_x.setDisabled(True)
        self.edit_scale_y.setDisabled(True)
        self.edit_scale_z.setDisabled(True)

        if self.scale_units == 'percent':
            self.edit_scale_x.setSuffix("%")
            self.edit_scale_x.setValue(mesh.scale[0] * 100)
            self.edit_scale_y.setSuffix("%")
            self.edit_scale_y.setValue(mesh.scale[1] * 100)
            self.edit_scale_z.setSuffix("%")
            self.edit_scale_z.setValue(mesh.scale[2] * 100)
        else:
            self.edit_scale_x.setSuffix("mm")
            self.edit_scale_x.setValue(mesh.scale[0] * mesh.size_origin[0] * 10)
            self.edit_scale_y.setSuffix("mm")
            self.edit_scale_y.setValue(mesh.scale[1] * mesh.size_origin[1] * 10)
            self.edit_scale_z.setSuffix("mm")
            self.edit_scale_z.setValue(mesh.scale[2] * mesh.size_origin[2] * 10)

        self.edit_scale_x.setDisabled(False)
        self.edit_scale_y.setDisabled(False)
        self.edit_scale_z.setDisabled(False)


    def change_scale_units(self):
        mesh = self.controller.get_object_by_id(self.object_id)
        if not mesh:
            return
        self.scale_units = self.combobox_scale_units.currentText()
        self.set_scale_widgets(mesh)

    def lock_scale_axes_change(self):
        self.lock_scale_axis = self.lock_scale_axes_checkbox.isChecked()
        if self.lock_scale_axis:
            self.scale_ration = [1.,.5,.5]


    def close_object_settings_panel(self):
        self.object_settings_panel.setVisible(False)
        self.line.setVisible(False)
        self.right_panel.setMaximumWidth(250)
        self.is_setting_panel_opened = False
        self.object_id = 0
        self.object_settings_panel.setFocusPolicy(Qt.NoFocus)
        self.glWidget.setFocusPolicy(Qt.StrongFocus)

    def apply_object_settings(self):
        object_id = self.get_object_id()
        mesh = self.controller.get_object_by_id(object_id)
        if not mesh:
            return
        mesh.apply_changes()
        #self.controller.scene.save_change(mesh)
        self.close_object_settings_panel()
        self.controller.view.update_scene()

    def cancel_object_settings(self):
        object_id = self.get_object_id()
        mesh = self.controller.get_object_by_id(object_id)
        if not mesh:
            return
        mesh.discard_changes()
        self.close_object_settings_panel()
        self.controller.view.update_scene()

    def set_position_on_object(self, widget, object_id, x, y, z, place_on_zero):
        if widget.hasFocus():
            self.controller.scene_was_changed()
            model = self.controller.get_object_by_id(object_id)
            if not model:
                return
            model.set_move(np.array([x*.1, y*.1, z*.1]), False, place_on_zero)
            self.controller.view.update_scene()

    def set_rotation_on_object(self, widget, object_id, x, y, z, place_on_zero):
        if widget.hasFocus():
            self.controller.scene_was_changed()
            model = self.controller.get_object_by_id(object_id)
            if not model:
                return
            model.set_rot(np.deg2rad(x), np.deg2rad(y), np.deg2rad(z), False, True, place_on_zero)
            self.controller.view.update_scene()

    def set_scale_on_object(self, widget, active_axis, object_id, x, y, z, place_on_zero):

        if widget.hasFocus():
            self.controller.scene_was_changed()
            model = self.controller.get_object_by_id(object_id)
            if not model:
                return
            if self.scale_units == 'percent':
                if self.lock_scale_axis:

                    if active_axis=='x':
                        x_recalc = x
                        x_ration = x/(model.scale[0]*100.)

                        y_recalc = (model.scale[1]*100.) * x_ration
                        self.edit_scale_y.setDisabled(True)
                        self.edit_scale_y.setValue(y_recalc)
                        self.edit_scale_y.setDisabled(False)
                        z_recalc = (model.scale[2]*100.) * x_ration
                        self.edit_scale_z.setDisabled(True)
                        self.edit_scale_z.setValue(z_recalc)
                        self.edit_scale_z.setDisabled(False)
                    elif active_axis=='y':
                        y_recalc = y
                        y_ration = y / (model.scale[1]*100.)

                        x_recalc = (model.scale[0]*100.) * y_ration
                        self.edit_scale_x.setDisabled(True)
                        self.edit_scale_x.setValue(x_recalc)
                        self.edit_scale_x.setDisabled(False)
                        z_recalc = (model.scale[2]*100.) * y_ration
                        self.edit_scale_z.setDisabled(True)
                        self.edit_scale_z.setValue(z_recalc)
                        self.edit_scale_z.setDisabled(False)
                    elif active_axis == 'z':
                        z_recalc = z
                        z_ration = z / (model.scale[2]*100.)

                        x_recalc = (model.scale[0]*100.) * z_ration
                        self.edit_scale_x.setDisabled(True)
                        self.edit_scale_x.setValue(x_recalc)
                        self.edit_scale_x.setDisabled(False)
                        y_recalc = (model.scale[1]*100.) * z_ration
                        self.edit_scale_y.setDisabled(True)
                        self.edit_scale_y.setValue(y_recalc)
                        self.edit_scale_y.setDisabled(False)
                else:
                    x_recalc = x
                    y_recalc = y
                    z_recalc = z

                model.set_scale_abs(x_recalc * .01, y_recalc * .01, z_recalc * .01)

            else:
                #mm
                if self.lock_scale_axis:
                    #x = (x/model.size_origin[0])*0.1
                    #y = (y/model.size_origin[1])*0.1
                    #z = (z/model.size_origin[2])*0.1
                    print("Vstupni parametry pro mm: %s %s %s" % (str(x), str(y), str(z)))

                    if active_axis == 'x':
                        x_recalc = x
                        x_ration = x / (model.scale[0] * 100.)

                        y_recalc = (model.scale[1] * 100.) * x_ration
                        self.edit_scale_y.setDisabled(True)
                        self.edit_scale_y.setValue(y_recalc)
                        self.edit_scale_y.setDisabled(False)
                        z_recalc = (model.scale[2] * 100.) * x_ration
                        self.edit_scale_z.setDisabled(True)
                        self.edit_scale_z.setValue(z_recalc)
                        self.edit_scale_z.setDisabled(False)
                    elif active_axis == 'y':
                        y_recalc = y
                        y_ration = y / (model.scale[1] * 100.)

                        x_recalc = (model.scale[0] * 100.) * y_ration
                        self.edit_scale_x.setDisabled(True)
                        self.edit_scale_x.setValue(x_recalc)
                        self.edit_scale_x.setDisabled(False)
                        z_recalc = (model.scale[2] * 100.) * y_ration
                        self.edit_scale_z.setDisabled(True)
                        self.edit_scale_z.setValue(z_recalc)
                        self.edit_scale_z.setDisabled(False)
                    elif active_axis == 'z':
                        z_recalc = z
                        z_ration = z / (model.scale[2] * 100.)

                        x_recalc = (model.scale[0] * 100.) * z_ration
                        self.edit_scale_x.setDisabled(True)
                        self.edit_scale_x.setValue(x_recalc)
                        self.edit_scale_x.setDisabled(False)
                        y_recalc = (model.scale[1] * 100.) * z_ration
                        self.edit_scale_y.setDisabled(True)
                        self.edit_scale_y.setValue(y_recalc)
                        self.edit_scale_y.setDisabled(False)

                    x_recalc *= .1
                    y_recalc *= .1
                    z_recalc *= .1

                    print("Vystupni parametry pro mm: %s %s %s" % (str(x_recalc), str(y_recalc), str(z_recalc)))
                    model.set_scale_abs(x_recalc, y_recalc, z_recalc)
                else:
                    model.set_scale_abs((x/model.size_origin[0])*0.1, (y/model.size_origin[1])*.1, (z/model.size_origin[2])*.1)

        #self.update_object_settings(self.object_id)
        self.controller.view.update_scene()

        '''
        if widget.hasFocus():
            model = self.controller.get_object_by_id(object_id)
            if not model:
                return
            self.edit_scale_x.setDisabled(True)
            self.edit_scale_y.setDisabled(True)
            self.edit_scale_z.setDisabled(True)
            if self.scale_units=='percent':
                #units percent
                if self.lock_scale_axis:
                    print("Vstupni parametry pro procenta: %s %s %s" % (str(x), str(y), str(z)))
                    #axis are locked
                    if active_axis == 'x':
                        x_recalc = x
                        x_ration = x / (model.scale[0] * 100)

                        y_recalc = (model.scale[1] * 100) * x_ration
                        z_recalc = (model.scale[2] * 100) * x_ration

                        self.edit_scale_y.setValue(int(y_recalc))
                        self.edit_scale_z.setValue(int(z_recalc))
                    elif active_axis == 'y':
                        y_recalc = y
                        y_ration = y / (model.scale[1] * 100)

                        x_recalc = (model.scale[0] * 100) * y_ration
                        z_recalc = (model.scale[2] * 100) * y_ration

                        self.edit_scale_x.setValue(int(x_recalc))
                        self.edit_scale_z.setValue(int(z_recalc))
                    elif active_axis == 'z':
                        z_recalc = z
                        z_ration = z / (model.scale[2] * 100)

                        x_recalc = (model.scale[0] * 100) * z_ration
                        y_recalc = (model.scale[1] * 100) * z_ration

                        self.edit_scale_x.setValue(int(x_recalc))
                        self.edit_scale_y.setValue(int(y_recalc))
                else:
                    #without axis lock
                    x_recalc = x*.01
                    y_recalc = y*.01
                    z_recalc = z*.01

                x_recalc *=.01
                y_recalc *=.01
                z_recalc *=.01



                print("Vystupni parametry pro procenta: %s %s %s" % (str(x_recalc), str(y_recalc), str(z_recalc)))
            else:
                #mm units
                if self.lock_scale_axis:
                    # axis are locked
                    print("Vstupni parametry pro mm: %s %s %s" % (str(x), str(y), str(z)))

                    if active_axis == 'x':
                        x_recalc = x
                        x_ration = x / (model.scale[0] * 100)

                        y_recalc = (model.scale[1] * 100) * x_ration
                        z_recalc = (model.scale[2] * 100) * x_ration
                    elif active_axis == 'y':
                        y_recalc = y
                        y_ration = y / (model.scale[1] * 100)

                        x_recalc = (model.scale[0] * 100) * y_ration
                        z_recalc = (model.scale[2] * 100) * y_ration
                    elif active_axis == 'z':
                        z_recalc = z
                        z_ration = z / (model.scale[2] * 100)

                        x_recalc = (model.scale[0] * 100) * z_ration
                        y_recalc = (model.scale[1] * 100) * z_ration


                else:
                    # without axis lock
                    x_recalc = (x/model.size_origin[0])*.1
                    y_recalc = (y/model.size_origin[1])*.1
                    z_recalc = (z/model.size_origin[2])*.1
                self.edit_scale_x.setValue(x_recalc * model.size_origin[0] * 10)
                self.edit_scale_y.setValue(y_recalc * model.size_origin[1] * 10)
                self.edit_scale_z.setValue(z_recalc * model.size_origin[2] * 10)

            model.set_scale_abs(x_recalc, y_recalc, z_recalc)

            self.edit_scale_x.setDisabled(False)
            self.edit_scale_y.setDisabled(False)
            self.edit_scale_z.setDisabled(False)

            #self.update_object_settings(self.object_id)
            self.controller.view.update_scene()
        '''
    '''
    def set_x_scale(self, object_id, x):
        model = self.controller.get_object_by_id(object_id)
        if not model:
            return

        if self.scale_units =="percent":
            x_recalc = x * 0.01
        else:
            x_recalc = (x/model.size_origin[0]) * 0.1

        x_ration = x_recalc / model.scale[0]

        if self.lock_scale_axis:
            y = model.scale[1] * x_ration
            z = model.scale[2] * x_ration
        else:
            y = model.scale[1]
            z = model.scale[2]

        model.set_scale_abs(x_recalc, y, z)

        print("Vystup nove funkce: %s %s %s" %(str(x_recalc), str(y), str(z)))
    '''


    def open_gcode_view(self):
        if self.is_setting_panel_opened:
            self.cancel_object_settings()
        self.right_panel.setMaximumWidth(350)
        self.gcode_panel.setVisible(True)
        self.gcode_slider.setTickInterval(1)
        self.gcode_slider.setSingleStep(1)
        self.line.setVisible(True)
        self.controller.view.update_scene()

    #def set_gcode_slider(self, number_of_layers=0, maximal_value=0):
    #    self.gcode_slider.setTickInterval(0)

    def close_gcode_view(self):
        self.gcode_panel.setVisible(False)
        self.line.setVisible(False)
        self.right_panel.setMaximumWidth(250)
        self.controller.view.update_scene()


    def open_settings_dialog(self):
        data, ok = SettingsDialog.get_settings_data(self.controller, self.parent())
        return data

    def open_printer_info_dialog(self):
        PrinterInfoDialog.get_printer_info_dialog(self.controller, self.parent())

    def open_about_dialog(self):
        AboutDialog.get_about_dialog(self.controller, self.parent())

    def open_firmware_dialog(self):
        data, ok = FirmwareUpdateDialog.get_firmware_update(self.controller, self.parent())

    def disable_generate_button(self):
        self.generateButton.setDisabled(True)

    def enable_generate_button(self):
        self.generateButton.setDisabled(False)

    def open_project_file_dialog(self):
        filters = "Prus (*.prus *.PRUS)"
        title = 'Open project file'
        open_at = "/home"
        data = QtGui.QFileDialog.getOpenFileName(None, title, open_at, filters)
        data = self.convert_file_path_to_unicode(data)
        return data

    def open_model_file_dialog(self):
        filters = "STL (*.stl *.STL)"
        title = "Import model file"
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
                print(str())
                self.statusBar().showMessage('Dropped file name is ' + str(url.toLocalFile().toLocal8Bit().data()))
                #TODO: Add network files
                path = url.toLocalFile().toLocal8Bit().data()
                #path = self.convert_file_path_to_unicode(url.path())
                self.controller.open_file(path)

            event.acceptProposedAction()
        else:
            super(PrusaControlView, self).dropEvent(event)

    def convert_file_path_to_unicode(self, path):
        codec = QtCore.QTextCodec.codecForName("UTF-16")
        converted_path = unicode(codec.fromUnicode(path), 'UTF-16')
        return converted_path


    def update_gui(self):
        self.controller.scene_was_changed()
        self.update_gui_for_material()

    def update_gui_for_material(self, set_materials=0):
        if set_materials:
            self.materialCombo.clear()
            labels, first = self.controller.get_printer_materials_labels_ls(self.controller.actual_printer)
            self.materialCombo.addItems(labels)
            self.materialCombo.setCurrentIndex(first)



        # material_label = self.materialCombo.currentText()
        material_label = self.materialCombo.currentText()

        material_printing_settings = self.controller.get_printing_settings_for_material_by_label(material_label)
        #print(str(material_printing_settings))

        # update print quality widget
        self.qualityCombo.clear()
        material_printing_settings_quality_ls, first = self.controller.get_printer_material_quality_labels_ls_by_material_label(material_label)
        #print("Quality list: " + str(material_printing_settings_quality_ls))
        self.qualityCombo.addItems(material_printing_settings_quality_ls)
        self.qualityCombo.setCurrentIndex(first)

        # infill slider
        self.infillSlider.setValue(material_printing_settings['infill'])
        self.infillSlider.setMinimum(material_printing_settings['infillRange'][0])
        self.infillSlider.setMaximum(material_printing_settings['infillRange'][1])

    def get_actual_printing_data(self):
        material_label = self.materialCombo.currentText()
        material_name = self.controller.get_material_name_by_material_label(material_label)
        quality_label = self.qualityCombo.currentText()
        quality_name = self.controller.get_material_quality_name_by_quality_label(material_name, quality_label)

        infill_value = self.infillSlider.value()
        brim = self.brimCheckBox.isChecked()
        #support = self.supportCheckBox.isChecked()
        support = self.supportCombo.currentText()

        data = {'material': material_name,
                'quality': quality_name,
                'infill': infill_value,
                'brim': brim,
                'support_on_off': support,
                'support_build_plate': support,
                'overhang': support
                }
        return data


    def add_camera_position(self, vec):
        self.glWidget.camera_position += vec

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

    def get_camera_direction(self, event):
        return self.glWidget.get_camera_direction(event)

    def get_tool_buttons(self):
        return self.glWidget.tools

    def update_scene(self, reset=False):
        self.glWidget.update_scene(reset)

    def set_gcode_slider(self, val):
        self.controller.set_gcode_layer(val)
        self.gcode_label.setText(self.controller.gcode.data_keys[val])

    #def set_gcode_draw_layers_from_button(self, val):
    #    self.controller.set_gcode_draw_from_button(val)
    #    self.controller.update_scene()

    def set_infill(self, val):
        self.infillValue = val
        self.infillLabel.setText(self.tr("Infill") + " " + str(val) + "%")

    def create_slider(self, setterSlot, defaultValue=0, rangeMin=0, rangeMax=100, orientation=QtCore.Qt.Horizontal):
        slider = QtGui.QSlider(orientation)

        slider.setRange(rangeMin, rangeMax)
        slider.setSingleStep(10)
        slider.setPageStep(20)
        slider.setTickInterval(10)
        slider.setValue(defaultValue)
        slider.setTickPosition(QtGui.QSlider.TicksRight)

        self.connect(slider, QtCore.SIGNAL("valueChanged(int)"), setterSlot)
        return slider
