# -*- coding: utf-8 -*-
import json
import logging

import functools


import time
import webbrowser
from pprint import pprint
from ConfigParser import RawConfigParser

from shutil import copyfile, Error

import numpy
import pyrr
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QApplication

import sceneData
from analyzer import Analyzer
from gcode import GCode
from gui import PrusaControlView
from parameters import AppParameters, PrintingParameters
from projectFile import ProjectFile
from sceneData import AppScene, ModelTypeStl
from sceneRender import GLWidget
from copy import deepcopy


import xml.etree.cElementTree as ET
from zipfile import ZipFile

from PyQt4 import QtCore, QtGui

#Mesure
from slicer import SlicerEngineManager


def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        logging.debug('%s function took %0.3f ms' % (f.func_name, (time2-time1)*1000.0))
        return ret
    return wrap

class Controller:
    def __init__(self, app, local_path=''):
        logging.info('Local path: ' + local_path)

        self.app_config = AppParameters(self, local_path)
        self.printing_parameters = PrintingParameters(self.app_config)

        self.analyzer = Analyzer(self)
        self.gcode = None

        self.printing_settings = {}
        self.settings = {}
        if not self.settings:
            self.settings['debug'] = self.app_config.config.getboolean('settings', 'debug')
            self.settings['automatic_placing'] = self.app_config.config.getboolean('settings', 'automatic_placing')
            self.settings['language'] = self.app_config.config.get('settings', 'language')
            self.settings['printer'] = self.app_config.config.get('settings', 'printer')
            self.settings['printer_type'] = self.app_config.config.get('settings', 'printer_type')
            self.settings['analyze'] = self.app_config.config.getboolean('settings', 'analyze')

            self.settings['toolButtons'] = {
                'selectButton': False,
                'moveButton': False,
                'rotateButton': False,
                'scaleButton': False
        }

        self.set_printer(self.settings['printer'])

        self.enumeration = {
            'language': {
                'cs_CZ': 'Czech',
                'en_US': 'English'
            },
            'printer': {
                'i3': 'i3',
                'i3_mk2': 'i3 mark2'
            },
            'materials': {
                'pla': 'PLA',
                'abs': 'ABS',
                'flex': 'FLEX'
            },
            'quality': {
                'draft': 'Draft',
                'normal': 'Normal',
                'detail': 'Detail',
                'ultradetail': 'Ultra detail'
            }
        }


        #variables for help
        self.last_pos = QtCore.QPoint()
        self.ray_start = [.0, .0, .0]
        self.ray_end = [.0, .0, .0]
        self.hitPoint = [.0, .0, .0]
        self.last_ray_pos = [.0, .0, .0]
        self.original_scale = 0.0
        self.original_scale_point = numpy.array([0.,0.,0.])
        self.origin_rotation_point = numpy.array([0.,0.,0.])
        self.res_old = numpy.array([0., 0., 0.])
        self.render_status = 'model_view'   #'gcode_view'
        self.status = 'edit'
        self.canceled = False

        self.gcode_layer = '0.0'
        self.gcode_draw_from_button = True

        self.over_object = False
        self.models_selected = False

        self.app = app
        self.app_parameters = app.arguments()

        self.translator = QtCore.QTranslator()
        self.set_language(self.settings['language'])

        self.scene = AppScene(self)
        self.view = PrusaControlView(self)
        self.slicer_manager = SlicerEngineManager(self)

        self.analyze_result = []

        self.tools = self.view.get_tool_buttons()
        self.tool = ''
        self.camera_move = False
        self.camera_rotate = False
        self.view.update_gui_for_material()

        logging.info('Parameters: %s' % ([unicode(i.toUtf8(), encoding="UTF-8") for i in self.app_parameters]))

        '''
        if len(self.app_parameters) >= 3:
            for file in self.app_parameters[2:]:
                logging.info('%s' %unicode(file.toUtf8(), encoding="UTF-8"))
                self.open_file(unicode(file.toUtf8(), encoding="UTF-8"))
        '''




    def write_config(self):
        config = RawConfigParser()
        config.add_section('settings')
        config.set('settings', 'printer', self.settings['printer'])
        config.set('settings', 'printer_type', self.settings['printer_type'])
        config.set('settings', 'debug', str(self.settings['debug']))
        config.set('settings', 'automatic_placing', str(self.settings['automatic_placing']))
        config.set('settings', 'language', self.settings['language'])

        with open(self.app_config.config_path, 'wb') as configfile:
            config.write(configfile)


    def read_gcode(self, filename = ''):
        if filename:
            self.gcode = GCode(filename)
        else:
            self.gcode = GCode(self.app_config.tmp_place + 'out.gcode')

        min = 0
        max = len(self.gcode.data_keys)-1

        self.view.gcode_slider.setMinimum(min)
        self.view.gcode_slider.setMaximum(max)

        min_l = float(self.gcode.data_keys[0])
        max_l = float(self.gcode.data_keys[-1])

        self.gcode_layer = self.gcode.data_keys[0]


        self.view.gcode_label.setText(self.gcode.data_keys[0])
        self.view.gcode_slider.setValue(float(self.gcode.data_keys[0]))

        if filename:
            self.set_gcode_view()

    def set_gcode_layer(self, value):
        self.gcode_layer = self.gcode.data_keys[value]
        self.view.update_scene()

    def set_gcode_draw_from_button(self, val):
        self.gcode_draw_from_button = val


    def scene_was_sliced(self):
        self.set_save_gcode_button()
        self.read_gcode()
        self.set_gcode_view()
        self.status = 'generated'


    def set_gcode_view(self):
        self.unselect_objects()
        self.render_status = 'gcode_view'
        self.open_gcode_gui()

    def set_model_edit_view(self):
        self.render_status = 'model_view'
        self.view.close_gcode_view()

    def open_gcode_gui(self):
        self.view.open_gcode_view()


    def close_gcode_gui(self):
        self.view.close_gcode_view()


    def set_language(self, language):
        full_name = 'translation/' + language + '.qm'
        self.translate_app(full_name)

    def translate_app(self, translation="translation/en_US.qm"):
        self.translator.load(translation)
        self.app.installTranslator(self.translator)

    def cancel_generation(self):
        self.slicer_manager.cancel()

    def get_enumeration(self, section, enum):
        return self.enumeration[section][enum] if section in self.enumeration and enum in self.enumeration[section] else str(section)+':'+str(enum)

    def get_printer_name(self):
        #TODO:Add code for read and detect printer name
        return "Original Prusa i3"

    def get_firmware_version_number(self):
        #TODO:Add code for download firmware version
        return '1.0.1'

    def get_printers_labels_ls(self):
        return [self.printing_parameters.get_printers_parameters()[printer]["label"] for printer in self.printing_parameters.get_printers_parameters()]

    def get_printers_names_ls(self):
        return self.printing_parameters.get_printers_names()

    def get_printer_variations_labels_ls(self, printer_name):
        printer_settings = self.printing_parameters.get_printer_parameters(printer_name)
        return [printer_settings["printer_type"][printer_type]["label"] for printer_type in printer_settings["printer_type"]]

    def get_printer_variations_names_ls(self, printer_name):
        printer_settings = self.printing_parameters.get_printer_parameters(printer_name)
        return printer_settings["printer_type"].keys()

    def get_printer_materials_names_ls(self, printer_name):
        #return self.printing_settings['materials']
        #return [i['label'] for i in self.printing_settings['materials'] if i['name'] not in ['default']]
        return self.printing_parameters.get_materials_for_printer(printer_name).keys()

    def get_printer_materials_labels_ls(self, printer_name):
        data = self.printing_parameters.get_materials_for_printer(printer_name)
        list = [[data[material]['label'], data[material]["sort"]] for material in data]
        list = sorted(list, key=lambda a: a[1])
        return [a[0] for a in list]

    def get_printer_material_quality_labels_ls_by_material_name(self, material_name):
        #return [self.printing_parameters.get_materials_quality_for_printer(self.actual_printer, material_name)['quality'][i]['label']
        #        for i in self.printing_parameters.get_materials_quality_for_printer(self.actual_printer, material_name)['quality']]
        data = self.printing_parameters.get_materials_quality_for_printer(self.actual_printer, material_name)['quality']
        list = [[data[quality]['label'], data[quality]["sort"]] for quality in data]
        list = sorted(list, key=lambda a: a[1])
        return [a[0] for a in list]

    def get_material_name_by_material_label(self, material_label):
        data = self.printing_parameters.get_materials_for_printer(self.actual_printer)
        for i in data:
            if data[i]['label']==material_label:
                return i
        return None

    def get_material_quality_name_by_quality_label(self, material_name, quality_label):
        data = self.printing_parameters.get_materials_for_printer(self.actual_printer)[material_name]
        for i in data["quality"]:
            if data["quality"][i]['label'] == quality_label:
                return i
        return None



    def get_printer_material_quality_labels_ls_by_material_label(self, material_label):
        materials_ls = self.printing_parameters.get_materials_for_printer(self.actual_printer)
        material_name = ""
        for material in materials_ls:
            if materials_ls[material]['label'] == material_label:
                material_name = material
                break

        return self.get_printer_material_quality_labels_ls_by_material_name(material_name)

    def get_printer_material_quality_names_ls(self, material):
        # return [i['label'] for i in self.printing_settings['materials'][index]['quality'] if i['name'] not in ['default']]
        data = self.printing_parameters.get_materials_quality_for_printer(self.actual_printer, material)['quality']
        list = [[quality, data[quality]["sort"]] for quality in data]
        list = sorted(list, key=lambda a: a[1])
        return [a[0] for a in list]
        #return [i for i in self.printing_parameters.get_materials_quality_for_printer(self.actual_printer, material)['quality']]


    def get_printing_settings_for_material_by_name(self, material_name):
        # material = self.printing_settings['materials'][material_index]
        printing_settings_tmp = []
        printing_settings_tmp = self.printing_parameters.get_materials_for_printer(self.actual_printer)
        material_printing_setting = printing_settings_tmp[material_name]

        return material_printing_setting

    def get_printing_settings_for_material_by_label(self, material_label):
        printing_settings_tmp = []
        for material in self.printing_parameters.get_materials_for_printer(self.actual_printer):
            if self.printing_parameters.get_materials_for_printer(self.actual_printer)[material]["label"] == material_label:
                printing_settings_tmp = self.printing_parameters.get_materials_for_printer(self.actual_printer)[material]
                break

        return printing_settings_tmp

    '''
    def get_printing_parameters_for_material_quality(self, material_index, quality_index):
        material_default = self.printing_settings['materials'][material_index]['quality'][-1]['parameters']
        material_quality = self.printing_settings['materials'][material_index]['quality'][quality_index]['parameters']
        default_material = deepcopy(self.printing_settings['materials'][-1]['quality'][0]['parameters'])
        data = default_material
        data.update(material_default)
        data.update(material_quality)
        return data
    '''

    def get_actual_printing_data(self):
        return self.view.get_actual_printing_data()

    def generate_button_pressed(self):
        whole_scene = self.scene.get_whole_scene_in_one_mesh()
        if self.status in ['edit', 'canceled']:
            #prepared to be g-code generated
            self.canceled = False
            if self.settings['analyze']:
                self.analyze_result = self.analyzer.make_analyze(whole_scene)
                self.make_reaction_on_analyzation_result(self.analyze_result)

            if not self.canceled:
                self.generate_gcode()
                self.set_cancel_button()
                self.status = 'generating'

        elif self.status == 'generating':
            #generating in progress
            self.cancel_generation()
            self.status = 'canceled'
            self.set_generate_button()
        elif self.status == 'generated':
            #already generated
            self.save_gcode_file()


    def make_reaction_on_analyzation_result(self, result):
        result_text = [i['message'] for i in result if i['result']==True]
        if result_text:
            result_text = "\n".join(result_text)

            msg = QtGui.QMessageBox()
            msg.setIcon(QtGui.QMessageBox.Warning)

            msg.setText("Do you want to apply recommended settings?")
            msg.setInformativeText("PrusaControl make analyze of printing scene, recommending different printing settings")
            msg.setWindowTitle("Analyze of printing scene")
            msg.setDetailedText(result_text)
            msg.setStandardButtons(QtGui.QMessageBox.Ignore | QtGui.QMessageBox.Apply | QtGui.QMessageBox.Cancel)
            msg.buttonClicked.connect(self.reaction_button_pressed)

            retval = msg.exec_()

    def reaction_button_pressed(self, i):
        if i.text() == 'Apply':
            for res in self.analyze_result:
                if res['result']:
                    widget_list = self.view.get_changable_widgets()
                    widget = widget_list[res['gui_name']]
                    widget.setChecked(True)
        elif i.text() == 'Cancel':
            self.canceled = True


    def open_web_browser(self, url):
        webbrowser.open(url, 1)

    def set_printer(self, name):
        #index = [i for i, data in enumerate(self.printers) if data['name']== name]
        self.actual_printer = name

    def send_feedback(self):
        if self.settings['language'] == 'cs_CZ':
            self.open_web_browser("http://goo.gl/forms/7jFBgXjOoqMbQ1wl1")
        else:
            self.open_web_browser("http://goo.gl/forms/nhKwtXvrtaZey0B02")

    def open_help(self):
        self.open_web_browser("http://www.prusa3d.com")

    def open_shop(self):
        self.open_web_browser("http://shop.prusa3d.com")

    def set_save_gcode_button(self):
        self.view.set_save_gcode_button()

    def set_cancel_button(self):
        self.view.set_cancel_button()

    def set_generate_button(self):
        self.view.set_generate_button()

    def update_gui(self):
        self.view.update_gui()

    def set_progress_bar(self, value):
        self.view.progressBar.setValue(value)

    def get_view(self):
        return self.view

    def get_model(self):
        return self.scene

    def open_printer_info(self):
        self.view.open_printer_info_dialog()

    def open_update_firmware(self):
        self.view.open_firmware_dialog()

    def open_project_file(self, url=None):
        if url:
            data = url
        else:
            data = self.view.open_project_file_dialog()
        #logging.debug('open project file %s' %data)
        self.import_project(data)

    def save_project_file(self):
        data = self.view.save_project_file_dialog()
        #logging.debug('save project file %s' %data)
        self.save_project(data)

    def save_gcode_file(self):
        data = self.view.save_gcode_file_dialog()
        filename = data.split('.')
        if filename[-1] in ['gcode', 'GCODE']:
            filename_out = data
        else:
            filename_out = data + '.gcode'
        try:
            copyfile(self.app_config.tmp_place + "out.gcode", filename_out)
        except Error as e:
            logging.debug('Error: %s' % e)
        except IOError as e:
            logging.debug('Error: %s' % e.strerror)

    def open_model_file(self):
        data = self.view.open_model_file_dialog()
        #logging.debug('open model file %s' %data)
        self.import_model(data)

    def import_model(self, path):
        self.view.statusBar().showMessage('Load file name: ' + path)
        model = ModelTypeStl().load(path)
        model.parent = self.scene
        self.scene.models.append(model)
        if self.settings['automatic_placing']:
            self.scene.automatic_models_position()
        self.scene.clear_history()
        for m in self.scene.models:
            self.scene.save_change(m)
        self.view.update_scene()

    def import_project(self, path):
        project_file = ProjectFile(self.scene, path)
        self.view.update_scene()

    def save_project(self, path):
        self.scene.check_models_name()
        project_file = ProjectFile(self.scene)
        project_file.save(path)

    def update_scene(self):
        self.view.update_scene()

    def update_firmware(self):
        #TODO:Add code for update of firmware
        pass

    def open_object_settings_dialog(self, object_id):
        object_settings = self.view.open_object_settings_dialog(object_id)

    def open_settings(self):
        self.settings = self.view.open_settings_dialog()

    def open_about(self):
        self.view.open_about_dialog()

    def generate_gcode(self):
        self.set_progress_bar(int(((10. / 9.) * 1) * 10))
        if self.scene.models:
            self.scene.save_whole_scene_to_one_stl_file(self.app_config.tmp_place + "tmp.stl")
            self.slicer_manager.slice()

    def gcode_generated(self):
        self.view.enable_save_gcode_button()

    def close(self):
        exit()

    def set_print_info_text(self, string):
        self.view.set_print_info_text(string)

    def scene_was_changed(self):
        self.status = 'edit'
        self.scene.analyze_result_data_tmp = []
        self.set_generate_button()
        self.set_progress_bar(0.0)

    def wheel_event(self, event):
        self.view.set_zoom(event.delta()/120)
        self.view.statusBar().showMessage("Zoom = %s" % self.view.get_zoom())
        self.view.update_scene()


    def set_camera_move_function(self):
        self.camera_move=True
        self.camera_rotate=False

    def set_camera_rotation_function(self):
        self.camera_move = False
        self.camera_rotate = True

    def set_camera_function_false(self):
        self.camera_move = False
        self.camera_rotate = False

    def is_some_tool_under_cursor(self, object_id):
        print("Is some tool under cursor")
        for tool in self.tools:
            if tool.id == object_id:
                return True
        return False

    def get_tool_by_id(self, object_id):
        for tool in self.tools:
            if tool.id == object_id:
                return tool
        return None

    def get_object_by_id(self, object_id):
        for model in self.scene.models:
            if object_id==model.id:
                return model
        return None


    def get_active_tool(self):
        return None

    def is_some_tool_helper_under_cursor(self, object_id):
        if object_id == 0:
            return False
        for model in self.scene.models:
            if model.rotateXId == object_id:
                model.selected = True
                model.rotationAxis = 'x'
                self.tool = 'rotate'
                return True
            elif model.rotateYId == object_id:
                model.selected = True
                model.rotationAxis = 'y'
                self.tool = 'rotate'
                return True
            elif model.rotateZId == object_id:
                model.selected = True
                model.rotationAxis = 'z'
                self.tool = 'rotate'
                return True
            else:
                model.rotationAxis = []

    def set_active_tool_helper_by_id(self, object_id):
        pass


    @staticmethod
    def is_ctrl_pressed():
        print("is_ctrl_pressed")
        modifiers = QtGui.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ControlModifier:
            return True
        else:
            return False

    def is_object_already_selected(self, object_id):
        for model in self.scene.models:
            #object founded
            if model.id == object_id:
                if model.selected:
                    #object is selected
                    return True
                else:
                    #object is not selected
                    return False
        #No object with id in scene.models
        return None


    def unselect_object(self, object_id):
        for model in self.scene.models:
            # object founded
            if model.id == object_id:
                model.selected = False
                return True
        return False

    def select_object(self, object_id):
        for model in self.scene.models:
            # object founded
            if model.id == object_id:
                model.selected = True
                return True
        return False

    def unselect_objects(self):
        for model in self.scene.models:
            model.selected = False

    def add_camera_position(self, vec):
        self.view.add_camera_position(vec)

    def check_rotation_axis(self, event):
        if self.settings['toolButtons']['rotateButton']:
            if self.find_object_and_rotation_axis_by_color(event):
                self.view.update_scene()

    def key_press_event(self, event):
        key = event.key()
        if key in [Qt.Key_Delete, Qt.Key_Backspace] and self.render_status == 'model_view':
            self.scene.delete_selected_models()



    def mouse_double_click(self, event):
        if self.render_status == 'model_view':
            object_id = self.get_id_under_cursor(event)
            if object_id == 0 or self.is_some_tool_under_cursor(object_id):
                return
            else:
                self.open_object_settings(object_id)


    def mouse_press_event(self, event):
        print("mouse press event")
        newRayStart, newRayEnd = self.view.get_cursor_position(event)
        self.res_old = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
        #Je stisknuto prave tlacitko?
        if event.button() & QtCore.Qt.RightButton:
            self.set_camera_move_function()
        #Je stisknuto leve tlacitko?
        elif event.button() & QtCore.Qt.LeftButton:
            #Je kurzor nad nejakym objektem?
            if self.render_status == 'model_view':
                object_id = self.get_id_under_cursor(event)
                if object_id==0:
                    self.set_camera_rotation_function()
                else:
                    #Je pod kurzorem nejaky tool?
                    if self.is_some_tool_under_cursor(object_id):
                        tool = self.get_tool_by_id(object_id)
                        for t in self.tools:
                            if not t == tool:
                                t.unpress_button()
                            else:
                                tool.press_button()
                        #tool.activate_tool()
                    #Je pod kurzorem nejaky tool helper?
                    elif self.is_some_tool_helper_under_cursor(object_id):
                        print("Nasel tool_helper")
                        self.set_active_tool_helper_by_id(object_id)
                    #Je objekt oznaceny?
                    elif self.is_ctrl_pressed():
                        if self.is_object_already_selected(object_id):
                            self.unselect_object(object_id)
                        else:
                            self.select_object(object_id)
                    elif self.is_object_already_selected(object_id):
                        #nastav funkci na provedeni toolu

                        self.tool = self.get_active_tool()
                        print("Aktualni tool je " + self.tool)

                        #TODO:add function get_active_tool(self) return class tool
                        #tool = self.get_toolsactive_tool()
                        #TODO:add function do(self) to class tool
                        self.prepare_tool(event)
                    else:
                        #select object
                        self.unselect_objects()
                        self.select_object(object_id)
            else:
                self.unselect_objects()
                self.set_camera_rotation_function()
        self.view.update_scene()

    def prepare_tool(self, event):
        if self.tool == 'rotate':
            newRayStart, newRayEnd = self.view.get_cursor_position(event)
            self.origin_rotation_point = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
            self.res_old = self.origin_rotation_point
            self.view.glWidget.oldHitPoint = numpy.array([0., 0., 0.])
            self.view.glWidget.hitPoint = numpy.array([0., 0., 0.])
        elif self.tool == 'placeonface':
            ray_start, ray_end = self.view.get_cursor_position(event)
            for model in self.scene.models:
                if model.selected:
                    self.view.glWidget.rayStart = ray_start
                    self.view.glWidget.rayDir = numpy.array(ray_end) - numpy.array(ray_start)
                    face = model.place_on_face(ray_start, ray_end)
                    if not face == []:
                        self.view.glWidget.v0 = face[0]
                        self.view.glWidget.v1 = face[1]
                        self.view.glWidget.v2 = face[2]
                        print("Nalezen objekt " + str(model))




    def get_active_tool(self):
        for tool in self.tools:
            if tool.pressed:
                return tool.tool_name
        return 'move'

    def mouse_release_event(self, event):
        print("mouse release event")
        self.set_camera_function_false()
        print("Hodnota v tool je: " + self.tool)
        if self.tool in ['move', 'rotate', 'scale', 'placeonface']:
            print("Ukladame nastaveni")
            for model in self.scene.models:
                if model.selected:
                    model.update_min_max()
                    model.recalc_bounding_sphere()
                    self.scene.save_change(model)
        self.tool = ''
        self.res_old = numpy.array([0.,0.,0.])

    def open_object_settings(self, object_id):
        self.view.create_object_settings_menu(object_id)

    def mouse_move_event(self, event):
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        #diff = numpy.linalg.norm(numpy.array([dx, dy]))

        if self.camera_move:
            camStart, camDir, camUp, camRight = self.view.get_camera_direction(event)
            right_move = -0.025*dx * camRight
            up_move = 0.025*dy * camUp

            move_vector = right_move + up_move
            self.add_camera_position(move_vector)

        elif self.camera_rotate:
            self.view.set_x_rotation(self.view.get_x_rotation() + 8 * dy)
            self.view.set_z_rotation(self.view.get_z_rotation() + 8 * dx)
            #camera_pos, direction, _, _ = self.view.get_camera_direction(event)
            #self.scene.camera_vector = direction - camera_pos
        #Move function
        elif self.tool== 'move':
            newRayStart, newRayEnd = self.view.get_cursor_position(event)
            res = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
            if res is not None:
                res_new = res - self.res_old
                for model in self.scene.models:
                    if model.selected:
                        model.set_move(res_new)
                        self.view.update_object_settings(model.id)
                        self.scene_was_changed()
                self.res_old = res

        #Rotate function
        elif self.tool == 'rotate':
            newRayStart, newRayEnd = self.view.get_cursor_position(event)
            res = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
            if res is not None:
                res_new = res - self.res_old
                for model in self.scene.models:
                    if model.selected:
                        pos = model.pos
                        pos[2] = 0.

                        #New
                        new_vec = res - pos
                        self.view.glWidget.hitPoint = deepcopy(new_vec)
                        new_vect_leng = numpy.linalg.norm(new_vec)
                        new_vec /= new_vect_leng

                        old_vec = self.res_old - pos
                        self.view.glWidget.oldHitPoint = deepcopy(old_vec)
                        old_vec /= numpy.linalg.norm(old_vec)


                        cos_ang = numpy.dot(old_vec, new_vec)
                        cross = numpy.cross(old_vec, new_vec)

                        neg = numpy.dot(cross, numpy.array([0., 0., 1.]))
                        sin_ang = numpy.linalg.norm(cross) * numpy.sign(neg) * -1.

                        alpha = numpy.arctan2(sin_ang, cos_ang)

                        if new_vect_leng >= model.boundingSphereSize:
                            model.set_rot(model.rot[0], model.rot[1], alpha)
                            print("New angle: " + str(numpy.degrees(alpha)))
                        else:
                            alpha_new = numpy.degrees(alpha) // 45
                            print("New round angle: " + str(alpha_new*45.))
                            model.set_rot(model.rot[0], model.rot[1], alpha_new*(numpy.pi*.25))

                        self.view.update_object_settings(model.id)
                        self.scene_was_changed()
                #self.res_old = res

        #Scale function
        elif self.tool == 'scale':
            ray_start, ray_end = self.view.get_cursor_position(event)
            camera_pos, direction, _, _ = self.view.get_camera_direction(event)

            for model in self.scene.models:
                if model.selected:
                    pos = model.pos
                    pos[2] = 0.
                    new_scale_point = numpy.array(sceneData.intersection_ray_plane(ray_start, ray_end, pos, direction))
                    new_scale_vec = new_scale_point - pos
                    l = numpy.linalg.norm(new_scale_vec)
                    model.set_scale_abs(l, l, l)
                    self.view.update_object_settings(model.id)
                    self.scene_was_changed()


        self.last_pos = QtCore.QPoint(event.pos())
        self.view.update_scene()


    '''
    def mouse_move_event(self, event):
        if event.buttons() & QtCore.Qt.LeftButton or event.buttons() & QtCore.Qt.RightButton:
            self.in_move = True
        elif self.settings['toolButtons']['rotateButton']:
            self.check_rotation_axis(event)
        else:
            return

        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        diff = numpy.linalg.norm(numpy.array([dx, dy]))

        newRayStart, newRayEnd = self.view.get_cursor_position(event)

        if event.buttons() & QtCore.Qt.LeftButton and self.over_object and self.models_selected:
            res = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
            if res is not None:
                #res_new = sceneData.Vector.minusAB(res, self.res_old)
                res_new = res - self.res_old
                for model in self.scene.models:
                    if model.selected:
                        model.set_move(res_new)
                        self.scene_was_changed()
                    self.res_old = res
                self.view.update_scene()

        elif event.buttons() & QtCore.Qt.LeftButton & self.settings['toolButtons']['rotateButton']:
            res = [.0, .0, .0]
            #find plane(axis) in which rotation will be made
            #newRayStart, newRayEnd = self.view.get_cursor_position(event)
            ray_start, ray_end = self.view.get_cursor_position(event)
            for model in self.scene.models:
                if model.selected and model.rotationAxis:

                    if model.rotationAxis == 'x':
                        rotation_axis = numpy.array([1.0, 0.0, 0.0])
                    elif model.rotationAxis == 'y':
                        rotation_axis = numpy.array([0.0, 1.0, 0.0])
                    elif model.rotationAxis == 'z':
                        rotation_axis = numpy.array([0.0, 0.0, 1.0])

                    res = numpy.array(sceneData.intersection_ray_plane(ray_start, ray_end, model.pos, rotation_axis))
                    new_vec = res - model.pos
                    new_vec /= numpy.linalg.norm(new_vec)
                    old_vec = self.origin_rotation_point - model.pos
                    old_vec /= numpy.linalg.norm(old_vec)

                    cos_ang = numpy.dot(old_vec, new_vec)
                    cross = numpy.cross(old_vec, new_vec)

                    neg = numpy.dot(cross, rotation_axis)
                    sin_ang = numpy.linalg.norm(cross) * numpy.sign(neg) *-1.

                    alpha = numpy.arctan2(sin_ang, cos_ang)

                    model.set_rotation(rotation_axis, alpha)

                    self.scene_was_changed()
                self.res_old = res
            self.view.update_scene()


        elif event.buttons() & QtCore.Qt.LeftButton & self.settings['toolButtons']['scaleButton']:
            res = [.0, .0, .0]
            camera_pos, direction, _ ,_   = self.view.get_camera_direction(event)
            ray_start, ray_end = self.view.get_cursor_position(event)
            for model in self.scene.models:
                #if model.selected and model.scaleAxis:
                    #if model.scaleAxis == 'xyz':
                if model.selected:
                    new_scale_point = numpy.array(sceneData.intersection_ray_plane(ray_start, ray_end, model.zeroPoint, direction))
                    new_scale_vec = new_scale_point - model.zeroPoint
                    l = numpy.linalg.norm(new_scale_vec)/self.original_scale
                    model.set_scale(numpy.array([l, l, l]))
                else:
                    res = [.0, .0, .0]
            self.scene_was_changed()
            self.res_old = res
            self.view.update_scene()

        elif event.buttons() & QtCore.Qt.LeftButton and not self.over_object:
            #TODO:Add controll of camera instance
            self.view.set_x_rotation(self.view.get_x_rotation() + 8 * dy)
            self.view.set_z_rotation(self.view.get_z_rotation() + 8 * dx)
            self.last_pos = QtCore.QPoint(event.pos())
            camera_pos, direction, _ ,_   = self.view.get_camera_direction(event)
            self.scene.camera_vector = direction - camera_pos
            self.view.update_scene()

        elif event.buttons() & QtCore.Qt.MiddleButton:
            #TODO:Make it better
            pos, _ = self.view.get_cursor_position(event)
            #plane = pyrr.plane.create_from_position(pos, normal)

            new_pos = numpy.array(pos)
            diff = (self.last_ray_pos - new_pos)
            self.last_ray_pos = new_pos
            self.view.add_camera_position(diff)
            #self.view.update_scene()
    '''

    def set_printable(self, is_printable):
        self.scene.printable = is_printable
        if is_printable == False:
            self.disable_generate_button()
        else:
            self.enable_generate_button()

    def disable_generate_button(self):
        self.view.disable_generate_button()

    def enable_generate_button(self):
        self.view.enable_generate_button()

    def hit_objects(self, event):
        possible_hit = []
        nSelected = 0

        self.ray_start, self.ray_end = self.view.get_cursor_position(event)

        for model in self.scene.models:
            if model.intersection_ray_bounding_sphere(self.ray_start, self.ray_end):
                possible_hit.append(model)
                nSelected+=1
            else:
                model.selected = False

        if not nSelected:
            return False

        for model in possible_hit:
            if model.intersection_ray_model(self.ray_start, self.ray_end):
                model.selected = not model.selected
            else:
                model.selected = False

        return False

    def hit_first_object(self, event):
        possible_hit = []
        nSelected = 0
        self.ray_start, self.ray_end = self.view.get_cursor_position(event)
        self.scene.clear_selected_models()

        for model in self.scene.models:
            if model.intersection_ray_bounding_sphere(self.ray_start, self.ray_end):
                possible_hit.append(model)
                nSelected+=1

        if not nSelected:
            return False

        for model in possible_hit:
            if model.intersection_ray_model(self.ray_start, self.ray_end):
                model.selected = True
                return True

        return False

#    @timing
    def get_id_under_cursor(self, event):
        return self.view.glWidget.get_id_under_cursor(event.x(), event.y())

    def hit_tool_button_by_color(self, event):
        find_id = self.get_id_under_cursor(event)
        if find_id == 0:
            return False
        id_list = [i.id for i in self.view.get_tool_buttons()]
        if find_id in id_list:
            for toolButton in self.view.get_tool_buttons():
                if find_id == toolButton.id:
                    toolButton.press_button()
                else:
                    toolButton.unpress_button()
        return False

    def hit_first_object_by_color(self, event, add=False):
        if not add:
            self.scene.clear_selected_models()
        find_id = self.get_id_under_cursor(event)
        if find_id == 0:
            return False
        for model in self.scene.models:
            if model.id == find_id:
                model.selected = not model.selected
                return True

    def find_object_and_rotation_axis_by_color(self, event):
        #color = self.view.get_cursor_pixel_color(event)
        #color to id
        find_id = self.get_id_under_cursor(event)
        if find_id == 0:
            return False
        for model in self.scene.models:
            if model.rotateXId == find_id:
                model.selected = True
                model.rotationAxis = 'x'
                return True
            elif model.rotateYId == find_id:
                model.selected = True
                model.rotationAxis = 'y'
                return True
            elif model.rotateZId == find_id:
                model.selected = True
                model.rotationAxis = 'z'
                return True
            else:
                model.rotationAxis = []

    def find_object_and_scale_axis_by_color(self, event):
        self.scene.clear_selected_models()
        find_id = self.get_id_under_cursor(event)
        if find_id == 0:
            return False
        for model in self.scene.models:
            if model.id == find_id:
                model.selected = True
                model.scaleAxis = 'xyz'
                return True

    def reset_scene(self):
        self.scene.clearScene()
        self.view.update_scene(True)

    def import_image(self, path):
        #TODO:Add importing of image(just plane with texture?)
        pass

    def undo_button_pressed(self):
        print("Undo")
        self.clear_tool_button_states()
        self.scene.make_undo()

    def do_button_pressed(self):
        print("Do")
        self.clear_tool_button_states()
        self.scene.make_do()

    def select_button_pressed(self):
        self.clear_tool_button_states()
        self.settings['toolButtons']['selectButton'] = True
        self.view.update_scene()

    def move_button_pressed(self):
        if self.settings['toolButtons']['moveButton']:
            self.settings['toolButtons']['moveButton'] = not(self.settings['toolButtons']['moveButton'])
        else:
            self.clear_tool_button_states()
            self.settings['toolButtons']['moveButton'] = True
        self.view.update_scene()

    def rotate_button_pressed(self):
        if self.settings['toolButtons']['rotateButton']:
            self.settings['toolButtons']['rotateButton'] = not(self.settings['toolButtons']['rotateButton'])
        else:
            self.clear_tool_button_states()
            self.settings['toolButtons']['rotateButton'] = True
        self.view.update_scene()

    def scale_button_pressed(self):
        if self.settings['toolButtons']['scaleButton']:
            self.settings['toolButtons']['scaleButton'] = not(self.settings['toolButtons']['scaleButton'])
        else:
            self.clear_tool_button_states()
            self.settings['toolButtons']['scaleButton'] = True
        self.view.update_scene()

    def place_on_face_button_pressed(self):
        #TODO:Add new tool
        pass

    def clear_tool_button_states(self):
        self.settings['toolButtons'] = {a: False for a in self.settings['toolButtons']}

    def show_message_on_status_bar(self, string):
        self.view.statusBar().showMessage(string)

    def open_file(self, url):
        '''
        function for resolve which file type will be loaded
        '''
        #self.view.statusBar().showMessage('Load file name: ')
        print("Soubor: %s " % url)
        if url[0] == '/' and self.app_config.system_platform in ['Windows']:
            url = url[1:]

        urlSplited = url.split('.')
        if len(urlSplited)>1:
            fileEnd = urlSplited[1]
        else:
            fileEnd=''

        if fileEnd in ['stl', 'STL', 'Stl']:
            print('import model')
            self.import_model(url)
        elif fileEnd in ['prus', 'PRUS']:
            print('open project')
            self.open_project_file(url)
        elif fileEnd in ['jpeg', 'jpg', 'png', 'bmp']:
            print('import image')
            self.import_image(url)
        elif fileEnd in ['gcode']:
            self.read_gcode(url)




