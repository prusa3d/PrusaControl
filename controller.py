# -*- coding: utf-8 -*-
import json
import logging

import functools
import os
import platform

import time
import webbrowser
from ConfigParser import ConfigParser, RawConfigParser
from pprint import pprint

from shutil import copyfile, Error

import numpy
import pyrr

import sceneData
from gui import PrusaControlView
from projectFile import ProjectFile
from sceneData import AppScene, ModelTypeStl
from sceneRender import GLWidget
from copy import deepcopy
import tempfile

import xml.etree.cElementTree as ET
from zipfile import ZipFile

from PyQt4 import QtCore

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
        logging.info('Controller instance created')

        self.system_platform = platform.system()
        self.config = ConfigParser()

        if self.system_platform in ['Linux']:
            self.tmp_place = tempfile.gettempdir() + '/'
            self.config_path = os.path.expanduser("~/.prusacontrol")
            self.printing_parameters_file = os.path.expanduser("data/printing_parameters.json")
            self.printers_parameters_file = os.path.expanduser("data/printers.json")
            self.config.readfp(open('data/defaults.cfg'))
        elif self.system_platform in ['Darwin']:
            self.tmp_place = tempfile.gettempdir() + '/'
            self.config_path = os.path.expanduser("~/.prusacontrol")
            self.printing_parameters_file = os.path.expanduser("data/printing_parameters.json")
            self.printers_parameters_file = os.path.expanduser("data/printers.json")
            self.config.readfp(open('data/defaults.cfg'))
        elif self.system_platform in ['Windows']:
            self.tmp_place = tempfile.gettempdir() + '\\'
            self.config_path = os.path.expanduser("~\\prusacontrol.cfg")
            self.printing_parameters_file = os.path.expanduser("data\\printing_parameters.json")
            self.printers_parameters_file = os.path.expanduser("data\\printers.json")
            self.config.readfp(open('data\\defaults.cfg'))
        else:
            self.tmp_place = './'
            self.config_path = 'prusacontrol.cfg'
            self.printing_parameters_file = "data/printing_parameters.json"
            self.printers_parameters_file = os.path.expanduser("data/printers.json")
            self.config.readfp(open('data/defaults.cfg'))

        self.config.read(self.config_path)

        self.printing_settings = {}
        self.settings = {}
        if not self.settings:
            self.settings['debug'] = self.config.getboolean('settings', 'debug')
            self.settings['automatic_placing'] = self.config.getboolean('settings', 'automatic_placing')
            self.settings['language'] = self.config.get('settings', 'language')
            self.settings['printer'] = self.config.get('settings', 'printer')

            self.settings['toolButtons'] = {
                'moveButton': False,
                'rotateButton': False,
                'scaleButton': False
        }


        with open(self.printing_parameters_file, 'rb') as json_file:
            self.printing_settings = json.load(json_file)

        with open(self.printers_parameters_file, 'rb') as json_file:
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

        self.app = app

        self.translator = QtCore.QTranslator()
        self.set_language(self.settings['language'])

        self.scene = AppScene(self)
        self.view = PrusaControlView(self)
        self.slicer_manager = SlicerEngineManager(self)


    def write_config(self):
        config = RawConfigParser()
        config.add_section('settings')
        config.set('settings', 'printer', self.settings['printer'])
        config.set('settings', 'debug', str(self.settings['debug']))
        config.set('settings', 'automatic_placing', str(self.settings['automatic_placing']))
        config.set('settings', 'language', self.settings['language'])

        with open(self.config_path, 'wb') as configfile:
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
            self.generate_gcode()
            self.set_cancel_button()
            self.status = 'generating'
        elif self.status == 'generating':
            self.cancel_generation()
            self.status = 'canceled'
            self.set_generate_button()
        elif self.status == 'generated':
            self.save_gcode_file()

    def open_web_browser(self, url):
        webbrowser.open(url, 1)

    def set_printer(self, name):
        index = [i for i, data in enumerate(self.printers) if data['name']== name]
        print(str(index))
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
        logging.debug('open project file %s' %data)
        self.import_project(data)

    def save_project_file(self):
        data = self.view.save_project_file_dialog()
        logging.debug('save project file %s' %data)
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
        logging.debug('open model file %s' %data)
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

    def open_settings(self):
        self.settings = self.view.open_settings_dialog()

    def open_about(self):
        self.view.open_about_dialog()

    def generate_gcode(self):
        self.set_progress_bar(int(((10. / 9.) * 1) * 10))
        if self.scene.models:
            self.scene.save_whole_scene_to_one_stl_file(self.tmp_place + "tmp.stl")
            self.slicer_manager.slice()

    def gcode_generated(self):
        self.view.enable_save_gcode_button()

    def close(self):
        exit()

    def set_print_info_text(self, string):
        self.view.set_print_info_text(string)

    def scene_was_changed(self):
        self.status = 'edit'
        self.set_generate_button()
        self.set_progress_bar(0.0)

    def wheel_event(self, event):
        self.view.set_zoom(event.delta()/120)
        self.view.statusBar().showMessage("Zoom = %s" % self.view.get_zoom())
        self.view.update_scene()

    def mouse_press_event(self, event):
        print("mouse press event")
        self.last_pos = QtCore.QPoint(event.pos())
        newRayStart, newRayEnd = self.view.get_cursor_position(event)
        if event.buttons() & QtCore.Qt.LeftButton:
            self.ray_start, self.ray_end = self.view.get_cursor_position(event)

        self.hit_tool_button_by_color(event)
        if event.buttons() & QtCore.Qt.LeftButton and self.settings['toolButtons']['moveButton']:
            self.res_old = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
            self.hitPoint = deepcopy(self.res_old)
            self.hit_first_object_by_color(event)
            for model in self.scene.models:
                if model.selected:
                    model.pos_old = deepcopy(model.pos)
        elif event.buttons() & QtCore.Qt.LeftButton and self.settings['toolButtons']['rotateButton']:
            for model in self.scene.models:
                if model.selected and model.rotationAxis:
                    if model.rotationAxis == 'x':
                        self.origin_rotation_point = numpy.array(sceneData.intersection_ray_plane(newRayStart, newRayEnd, model.pos, [1.0, 0.0, 0.0]))
                    elif model.rotationAxis == 'y':
                        self.origin_rotation_point = numpy.array(sceneData.intersection_ray_plane(newRayStart, newRayEnd, model.pos, [0.0, 1.0, 0.0]))
                    elif model.rotationAxis == 'z':
                        self.origin_rotation_point = numpy.array(sceneData.intersection_ray_plane(newRayStart, newRayEnd, model.pos, [0.0, 0.0, 1.0]))
                    self.hitPoint = deepcopy(self.origin_rotation_point)
        elif event.buttons() & QtCore.Qt.LeftButton and self.settings['toolButtons']['scaleButton']:
            self.find_object_and_scale_axis_by_color(event)
            for model in self.scene.models:
                if model.selected and model.scaleAxis:
                    camera_pos, direction, _, _ = self.view.get_camera_direction(event)
                    ray_start, ray_end = self.view.get_cursor_position(event)
                    self.original_scale_point = numpy.array(sceneData.intersection_ray_plane(ray_start, ray_end, model.zeroPoint, direction))
                    self.original_scale = numpy.linalg.norm(self.original_scale_point - model.zeroPoint)
                    self.hitPoint = deepcopy(self.original_scale_point)

        elif event.buttons() & QtCore.Qt.MiddleButton:
            rayStart,_  = self.view.get_cursor_position(event)
            self.last_ray_pos = numpy.array(rayStart)
        self.view.update_scene()

    def mouse_release_event(self, event):
        print("mouse release event")
        if event.button() & QtCore.Qt.LeftButton & self.settings['toolButtons']['rotateButton']:
            for model in self.scene.models:
                if model.selected:
                    model.apply_rotation()
                    model.rot = numpy.array([0.,0.,0.])
                    model.place_on_zero()
                    self.scene.save_change(model)
        elif event.button() & QtCore.Qt.LeftButton & self.settings['toolButtons']['moveButton']:
            for model in self.scene.models:
                if model.selected:
                    self.scene.save_change(model)
        elif event.button() & QtCore.Qt.LeftButton & self.settings['toolButtons']['scaleButton']:
            for model in self.scene.models:
                if model.selected and model.scaleAxis:
                    model.apply_scale()
                    self.scene.save_change(model)


        self.scene.clear_selected_models()
        self.view.update_scene()
        self.last_ray_pos = numpy.array([.0,.0,.0])

    def check_rotation_axis(self, event):
        if self.settings['toolButtons']['rotateButton']:
            if self.find_object_and_rotation_axis_by_color(event):
                self.view.update_scene()

    def mouse_move_event(self, event):
        print("mouse move event")
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        diff = numpy.linalg.norm(numpy.array([dx, dy]))
        newRayStart, newRayEnd = self.view.get_cursor_position(event)

        if event.buttons() & QtCore.Qt.LeftButton & self.settings['toolButtons']['moveButton']:
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
                if model.selected and model.scaleAxis:
                    if model.scaleAxis == 'xyz':
                        new_scale_point = numpy.array(sceneData.intersection_ray_plane(ray_start, ray_end, model.zeroPoint, direction))
                        new_scale_vec = new_scale_point - model.zeroPoint
                        l = numpy.linalg.norm(new_scale_vec)/self.original_scale
                        model.set_scale(numpy.array([l, l, l]))
                    else:
                        res = [.0, .0, .0]
                    self.scene_was_changed()
                self.res_old = res
            self.view.update_scene()

        elif event.buttons() & QtCore.Qt.RightButton:
            #TODO:Add controll of camera instance
            self.view.set_x_rotation(self.view.get_x_rotation() + 8 * dy)
            self.view.set_z_rotation(self.view.get_z_rotation() + 8 * dx)
            self.last_pos = QtCore.QPoint(event.pos())
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
    def hit_tool_button_by_color(self, event):
        color = self.view.get_cursor_pixel_color(event)
        find_id = color[0] + (color[1]*256) + (color[2]*256*256)
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

    def hit_first_object_by_color(self, event):
        self.scene.clear_selected_models()
        color = self.view.get_cursor_pixel_color(event)
        #color to id
        find_id = color[0] + (color[1]*256) + (color[2]*256*256)
        if find_id == 0:
            return False
        for model in self.scene.models:
            if model.id == find_id:
                model.selected = True
                return True

    def find_object_and_rotation_axis_by_color(self, event):
        color = self.view.get_cursor_pixel_color(event)
        #color to id
        find_id = color[0] + (color[1]*256) + (color[2]*256*256)
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
        color = self.view.get_cursor_pixel_color(event)
        #color to id
        find_id = color[0] + (color[1]*256) + (color[2]*256*256)
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
        self.settings['toolButtons']['moveButton'] = True
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
        if url[0] == '/' and self.system_platform in ['Windows']:
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




