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
from PyQt4.QtGui import QApplication

import sceneData
from analyzer import Analyzer
from gui import PrusaControlView
from parameters import AppParameters
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
    def __init__(self, app):
        #logging.info('Controller instance created')

        self.app_config = AppParameters()
        self.analyzer = Analyzer(self)



        self.printing_settings = {}
        self.settings = {}
        if not self.settings:
            self.settings['debug'] = self.app_config.config.getboolean('settings', 'debug')
            self.settings['automatic_placing'] = self.app_config.config.getboolean('settings', 'automatic_placing')
            self.settings['language'] = self.app_config.config.get('settings', 'language')
            self.settings['printer'] = self.app_config.config.get('settings', 'printer')

            self.settings['toolButtons'] = {
                'selectButton': False,
                'moveButton': False,
                'rotateButton': False,
                'scaleButton': False
        }


        with open(self.app_config.printing_parameters_file, 'rb') as json_file:
            self.printing_settings = json.load(json_file)

        with open(self.app_config.printers_parameters_file, 'rb') as json_file:
            self.printers = json.load(json_file)
            self.printers = self.printers['printers']

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
        self.res_old = numpy.array([0.,0.,0.])
        self.status = 'edit'
        self.canceled = False

        self.over_object = False
        self.models_selected = False


        self.app = app

        self.translator = QtCore.QTranslator()
        self.set_language(self.settings['language'])

        self.scene = AppScene(self)
        self.view = PrusaControlView(self)
        self.slicer_manager = SlicerEngineManager(self)

        self.analyze_result = []

        self.tool = ''
        self.camera_move = False
        self.camera_rotate = False


    def write_config(self):
        config = RawConfigParser()
        config.add_section('settings')
        config.set('settings', 'printer', self.settings['printer'])
        config.set('settings', 'debug', str(self.settings['debug']))
        config.set('settings', 'automatic_placing', str(self.settings['automatic_placing']))
        config.set('settings', 'language', self.settings['language'])

        with open(self.app_config.config_path, 'wb') as configfile:
            config.write(configfile)


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

    def get_printing_materials(self):
        #return self.printing_settings['materials']
        return [i['label'] for i in self.printing_settings['materials'] if i['name'] not in ['default']]

    def get_printing_material_quality(self, index):
        return [i['label'] for i in self.printing_settings['materials'][index]['quality'] if i['name'] not in ['default']]

    def get_printing_settings_for_material(self, material_index):
        material = self.printing_settings['materials'][material_index]

        #default
        printing_settings_tmp = deepcopy(self.printing_settings['materials'][-1])

        printing_settings_tmp.update(material)

        return printing_settings_tmp

    def get_printing_parameters_for_material_quality(self, material_index, quality_index):
        material_default = self.printing_settings['materials'][material_index]['quality'][-1]['parameters']
        material_quality = self.printing_settings['materials'][material_index]['quality'][quality_index]['parameters']
        default_material = deepcopy(self.printing_settings['materials'][-1]['quality'][0]['parameters'])
        data = default_material
        data.update(material_default)
        data.update(material_quality)
        return data

    def get_actual_printing_data(self):
        return self.view.get_actual_printing_data()

    def generate_button_pressed(self):
        if self.status in ['edit', 'canceled']:
            #prepared to be g-code generated
            self.analyze_result = self.analyzer.make_analyze(self.scene)
            self.canceled = False
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
        elif i.text() == '&Cancel':
            self.canceled = True


    def open_web_browser(self, url):
        webbrowser.open(url, 1)

    def set_printer(self, name):
        index = [i for i, data in enumerate(self.printers) if data['name']== name]
        #print(str(index))
        self.actual_printer = self.printers[index[0]]

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
        self.view.set_progress_bar(value)

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
            copyfile(self.tmp_place + "out.gcode", filename_out)
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
        self.scene.save_change(model)
        self.view.update_scene()

    def import_project(self, path):
        project_file = ProjectFile(self.scene, path)
        self.view.update_scene()

    def save_project(self, path):
        self.scene.check_models_name()
        project_file = ProjectFile(self.scene)
        project_file.save(path)

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
        #TODO:repair this bug
        #self.set_generate_button()
        #self.set_progress_bar(0.0)

    def key_press_event(self, event):
        print("key press event")
        if event.key() == QtCore.Qt.Key_Delete:
            self.scene.delete_selected_models()

    def wheel_event(self, event):
        self.view.set_zoom(event.delta()/120)
        self.view.statusBar().showMessage("Zoom = %s" % self.view.get_zoom())
        self.view.update_scene()

    def mouse_double_click(self, event):
        object_id = self.get_id_under_cursor(event)
        if object_id==0:
            return
        else:
            self.open_object_settings_dialog(object_id)

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
        #TODO:Add tools list
        '''
        for tool in self.tools:
            if tool.id == object_id:
                return True
            else:
                return False
        return False
        '''
        return False

    def get_tool_by_id(self, object_id):
        for tool in self.tools:
            if tool.id == object_id:
                return tool
        return None


    def get_active_tool(self):
        return None

    def is_some_tool_helper_under_cursor(self, object_id):
        return False

    def set_active_tool_helper_by_id(self, object_id):
        pass


    @staticmethod
    def is_ctrl_pressed():
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

    def check_rotation_axis(self, event):
        if self.settings['toolButtons']['rotateButton']:
            if self.find_object_and_rotation_axis_by_color(event):
                self.view.update_scene()


    def mouse_press_event(self, event):
        print("mouse press event")
        #je stisknuto prave tlacitko?
        if event.button() & QtCore.Qt.RightButton:
            #TODO:add function set_camera_rotation_function(self)
            self.set_camera_move_function()
        # je stisknuto leve tlacitko?
        elif event.button() & QtCore.Qt.LeftButton:
            #Je kurzor nad nejakym objektem?
            object_id = self.get_id_under_cursor(event)
            if object_id==0:
                #TODO:add function set_camera_rotation_function(self)
                self.set_camera_rotation_function()
            else:
                #Je pod kurzorem nejaky tool?
                #TODO:add function is_some_tool_under_cursor(self, object_id)
                if self.is_some_tool_under_cursor(object_id):
                    #TODO:add function get_tool_by_id(self, object_id)
                    tool = self.get_tool_by_id(object_id)
                    #TODO:add function activate_tool(self, object_id), and class tool
                    tool.activate_tool()
                #Je pod kurzorem nejaky tool helper?
                #TODO:add function
                elif self.is_some_tool_helper_under_cursor(object_id):
                    #TODO:add function set_active_tool_helper_by_id(self, object_id)
                    self.set_active_tool_helper_by_id(object_id)
                #Je objekt oznaceny?
                #TODO:add function is_object_already_selected(self, object_id)
                elif self.is_ctrl_pressed():
                    if self.is_object_already_selected(object_id):
                        self.unselect_object(object_id)
                    else:
                        self.select_object(object_id)
                elif self.is_object_already_selected(object_id):
                    #nastav funkci na provedeni toolu

                    self.tool = 'move'
                    #TODO:add function get_active_tool(self) return class tool
                    #tool = self.get_active_tool()
                    #TODO:add function do(self) to class tool
                    #tool.do()
                else:
                    #select object
                    #TODO:add function select_object(self, object_id)
                    self.unselect_objects()
                    self.select_object(object_id)
        self.view.update_scene()

    def mouse_release_event(self, event):
        print("mouse release event")
        self.set_camera_function_false()
        if self.tool == 'move':
            for model in self.scene.models:
                if model.selected:
                    self.scene.save_change(model)
        self.tool = ''



    def mouse_move_event(self, event):
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        #diff = numpy.linalg.norm(numpy.array([dx, dy]))
        newRayStart, newRayEnd = self.view.get_cursor_position(event)
        if self.camera_move:
            print("camera move")
            pass
        elif self.camera_rotate:
            print("camera rotate")
            self.view.set_x_rotation(self.view.get_x_rotation() + 8 * dy)
            self.view.set_z_rotation(self.view.get_z_rotation() + 8 * dx)
            self.last_pos = QtCore.QPoint(event.pos())
            #camera_pos, direction, _, _ = self.view.get_camera_direction(event)
            #self.scene.camera_vector = direction - camera_pos
        elif self.tool=='move':
            res = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
            if res is not None:
                res_new = res - self.res_old
                for model in self.scene.models:
                    if model.selected:
                        model.set_move(res_new)
                        self.scene_was_changed()
                    self.res_old = res
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
        print("founded id: " + str(find_id))
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
        print("founded id: " + str(find_id))
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
        print("founded id: " + str(find_id))
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
        print("founded id: " + str(find_id))
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
        self.clear_tool_button_states()
        self.scene.make_undo()

    def do_button_pressed(self):
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

    def clear_tool_button_states(self):
        self.settings['toolButtons'] = {a: False for a in self.settings['toolButtons']}

    def show_message_on_status_bar(self, string):
        self.view.statusBar().showMessage(string)

    def open_file(self, url):
        '''
        function for resolve which file type will be loaded
        '''
        #self.view.statusBar().showMessage('Load file name: ')
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




