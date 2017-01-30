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
from gui import PrusaControlView, QMessageBox
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
            self.settings['automatic_update_parameters'] = self.app_config.config.getboolean('settings', 'automatic_update_parameters')

            self.settings['toolButtons'] = {
                'selectButton': False,
                'moveButton': False,
                'rotateButton': False,
                'scaleButton': False,
                'supportButton': False
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

        self.warning_message_buffer = []


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
        self.is_model_loaded = False
        self.canceled = False
        self.filament_use = ''
        self.resolution_of_texture = 16

        #event flow flags
        self.mouse_double_click_event_flag = False
        self.mouse_press_event_flag = False
        self.mouse_move_event_flag = False
        self.mouse_release_event_flag = False
        self.tool_press_event_flag = False
        self.tool_helper_press_event_flag = False
        self.object_select_event_flag = False
        self.cursor_over_object = False

        #scene work flags
        self.scene_was_saved = False
        self.scene_was_generated = False
        self.gcode_was_saved = False
        self.scene_is_not_empty = True

        self.printer_number_of_materials = False

        self.gcode_layer = '0.0'
        self.gcode_draw_from_button = True

        self.over_object = False
        self.models_selected = False
        self.advance_settings = False

        self.app = app
        self.app_parameters = app.arguments()
        self.dpi_coef = app.desktop().logicalDpiX()/96.
        self.dpi_scale = 0 if self.dpi_coef==1.0 else 2

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

        printer_settings = self.printing_parameters.get_printer_parameters(self.settings['printer'])
        self.printer_number_of_materials = printer_settings['multimaterial']
        if self.printer_number_of_materials > 1:
            self.view.set_multimaterial_gui_on(self.printer_number_of_materials)
        else:
            self.view.set_multimaterial_gui_off()


        logging.info('Parameters: %s' % ([unicode(i.toUtf8(), encoding="UTF-8") for i in self.app_parameters]))

        if len(self.app_parameters) >= 3:
            for file in self.app_parameters[2:]:
                logging.info('%s' %unicode(file.toUtf8(), encoding="UTF-8"))
                self.open_file(unicode(file.toUtf8(), encoding="UTF-8"))


    def exit_event(self):
        if self.status in ['loading_gcode']:
            self.gcode.cancel()
            return True
        elif self.status in ['generating']:
            ret = self.view.show_exit_message_generating_scene()
            if ret == QMessageBox.Yes:
                self.cancel_generation()
                return True
            elif ret == QMessageBox.No:
                return False
        elif self.is_something_to_save() and not self.scene_was_saved:
            ret = self.view.show_exit_message_scene_not_saved()
            if ret == QMessageBox.Save:
                self.save_project_file()
                return True
            elif ret == QMessageBox.Discard:
                return True
            elif ret == QMessageBox.Cancel:
                return False
        else:
            return True



    def is_something_to_save(self):
        models_lst = [m for m in self.scene.models if m.isVisible]
        if len(models_lst) == 0:
            return False
        else:
            return True

    def get_informations(self):
        if not self.gcode:
            print("Neni gcode instance")
            return

        printing_time = self.gcode.printing_time
        filament_length = self.filament_use

        printing_time_str = self.convert_printing_time_from_seconds(printing_time)
        filament_length_str = "%s" % (filament_length)

        data = {'info_text': 'info total:',
                'printing_time': printing_time_str,
                'filament_lenght': filament_length_str}

        return data

    #TODO:Add some human readable form of printing time
    def convert_printing_time_from_seconds(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%02d:%02d" % (h, m)


    def clear_event_flag_status(self):
        self.mouse_double_click_event_flag = False
        self.mouse_press_event_flag = False
        self.mouse_move_event_flag = False
        self.mouse_release_event_flag = False
        self.tool_press_event_flag = False
        self.object_select_event_flag = False
        self.tool_helper_press_event_flag = False
        self.cursor_over_object = False

    def clear_gcode(self):
        self.gcode = None
        self.gcode_layer = '0.0'
        self.gcode_draw_from_button = False


    def write_config(self):
        config = RawConfigParser()
        config.add_section('settings')
        config.set('settings', 'printer', self.settings['printer'])
        config.set('settings', 'printer_type', self.settings['printer_type'])
        config.set('settings', 'debug', str(self.settings['debug']))
        config.set('settings', 'automatic_placing', str(self.settings['automatic_placing']))
        config.set('settings', 'language', self.settings['language'])
        config.set('settings', 'analyze', self.settings['analyze'])
        config.set('settings', 'automatic_update_parameters', self.settings['automatic_update_parameters'])


        with open(self.app_config.config_path, 'wb') as configfile:
            config.write(configfile)

    def set_basic_settings(self):
        self.advance_settings = False
        self.view.object_variable_layer_box.setVisible(False)
        self.view.object_group_box.setVisible(True)
        self.update_scene()

    def set_advance_settings(self):
        self.advance_settings = True
        self.view.object_group_box.setVisible(False)
        self.view.object_variable_layer_box.setVisible(True)
        #self.view.variable_layer_widget.set_model(self.ac)
        self.update_scene()

    def set_gcode_slider(self, min, max, min_l, max_l):
        '''
        self.view.gcode_slider.setMinimum(min)
        self.view.gcode_slider.setMaximum(max)

        self.view.gcode_slider_min_l.setText(str(min_l))
        self.view.gcode_slider_max_l.setText(str(max_l))
        '''

        self.view.gcode_slider.setMinimum(min)
        self.view.gcode_slider.setMaximum(max)

        self.view.gcode_slider.min_label.setText(str(min_l))
        self.view.gcode_slider.max_label.setText(str(max_l))


    def set_gcode_instance(self, gcode_instance):
        self.gcode = gcode_instance
        self.set_gcode()

    def print_progress(self, progress):
        print("Progress: " + str(progress))


    def read_gcode(self, filename = ''):
        if filename:
            self.gcode = GCode(filename, self, self.set_gcode)
        else:
            self.gcode = GCode(self.app_config.tmp_place + 'out.gcode', self, self.set_gcode)

        self.view.set_cancel_of_loading_gcode_file()
        self.status = 'loading_gcode'
        self.gcode.read_in_thread(self.set_progress_bar, self.set_gcode)


    def set_gcode(self):
        print("Set gcode")
        if not self.gcode.is_loaded:
            return
        self.status = 'generated'

        min = 0
        max = len(self.gcode.data_keys) - 1

        min_l = float(self.gcode.data_keys[0])
        max_l = float(self.gcode.data_keys[-1])

        self.set_gcode_slider(min, max, min_l, max_l)

        self.gcode_layer = self.gcode.data_keys[0]

        self.view.gcode_label.setText(self.gcode.data_keys[0])
        self.view.gcode_slider.setValue(float(self.gcode.data_keys[0]))

        self.set_gcode_view()

    def set_variable_layer_cursor(self, double_value):
        for m in self.scene.models:
            if m.isVisible and m.selected:
                m.z_cursor = double_value
        self.update_scene()


    def set_gcode_layer(self, value):
        self.gcode_layer = self.gcode.data_keys[value]
        self.update_scene()
        #self.view.update_scene()

    def set_gcode_draw_from_button(self, val):
        self.gcode_draw_from_button = val

    def scene_was_sliced(self):
        #self.set_save_gcode_button()
        #self.read_gcode()
        self.view.gcode_slider.init_points()
        self.set_gcode_view()
        self.status = 'generated'

    def check_rotation_helper(self, event):
        print("check rotation")
        id = self.get_id_under_cursor(event)
        if self.is_some_tool_under_cursor(id):
            self.view.update_scene()

    def unselect_tool_buttons(self):
        for tool in self.tools:
            tool.unpress_button()


    def set_gcode_view(self):
        self.unselect_objects()
        self.render_status = 'gcode_view'
        #self.view.set_gcode_slider()
        self.open_gcode_gui()

    def set_model_edit_view(self):
        self.render_status = 'model_view'
        self.set_generate_button()
        self.view.enable_editing()
        self.status = 'edit'
        #self.editable = editable
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
        #print("Nastaveni tiskaren: ")
        #pprint(printer_settings)
        return [printer_settings["printer_type"][printer_type]["label"] for printer_type in printer_settings["printer_type"]]

    def get_printer_variations_names_ls(self, printer_name):
        printer_settings = self.printing_parameters.get_printer_parameters(printer_name)
        return printer_settings["printer_type"].keys()

    def get_printer_materials_names_ls(self, printer_name):
        #return self.printing_settings['materials']
        #return [i['label'] for i in self.printing_settings['materials'] if i['name'] not in ['default']]
        return self.printing_parameters.get_materials_for_printer(printer_name).keys()

    def get_printer_materials_labels_ls(self, printer_name):
        first_index = 0
        data = self.printing_parameters.get_materials_for_printer(printer_name)
        list = [[data[material]['label'], data[material]["sort"], data[material]["first"]] for material in data]
        list = sorted(list, key=lambda a: a[1])
        for i, data in enumerate(list):
            if data[2] == 1:
                first_index = i
                break
        return [a[0] for a in list], first_index

    def get_printer_material_quality_labels_ls_by_material_name(self, material_name):
        #return [self.printing_parameters.get_materials_quality_for_printer(self.actual_printer, material_name)['quality'][i]['label']
        #        for i in self.printing_parameters.get_materials_quality_for_printer(self.actual_printer, material_name)['quality']]
        first_index = 0
        data = self.printing_parameters.get_materials_quality_for_printer(self.actual_printer, material_name)['quality']
        list = [[data[quality]['label'], data[quality]["sort"], data[quality]["first"]] for quality in data]
        list = sorted(list, key=lambda a: a[1])
        for i, data in enumerate(list):
            if data[2] == 1:
                first_index = i
                break
        return [a[0] for a in list], first_index

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

    def get_infill_ls_and_index_of_default(self, default):
        first = 0
        infill_ls = ["0%", "10%", "15%", "20%", "25%", "30%", "50%", "70%"]
        for i, data in enumerate(infill_ls):
            if data == default:
                first = i
                break

        return infill_ls, first

    def get_actual_printing_data(self):
        return self.view.get_actual_printing_data()


    def open_cancel_generating_dialog(self):
        ret = self.view.show_cancel_generating_dialog_and_load_file()
        if ret == QtGui.QMessageBox.Yes:
            self.cancel_generation()
            return True
        elif ret == QtGui.QMessageBox.No:
            return False


    def open_cancel_gcode_reading_dialog(self):
        ret = self.view.show_cancel_generating_dialog_and_load_file()
        if ret == QtGui.QMessageBox.Yes:
            self.cancel_gcode_loading()
            return True
        elif ret == QtGui.QMessageBox.No:
            return False

    def generate_button_pressed(self):
        if self.status in ['edit', 'canceled']:
            self.clear_tool_button_states()
            whole_scene = self.scene.get_whole_scene_in_one_mesh()
            #prepared to be g-code generated
            self.canceled = False
            self.close_object_settings()
            if self.settings['analyze']:
                self.analyze_result = self.analyzer.make_analyze(whole_scene)
                self.make_reaction_on_analyzation_result(self.analyze_result)
            self.view.disable_editing()

            if not self.canceled:
                self.generate_gcode()
                self.set_cancel_button()
                self.status = 'generating'

        elif self.status == 'generating':
            #generating in progress
            self.view.enable_editing()
            self.cancel_generation()
            self.status = 'canceled'
            self.set_generate_button()

        elif self.status == 'loading_gcode':
            self.cancel_gcode_loading()
        elif self.status == 'generated':
            #already generated
            self.save_gcode_file()


    def cancel_gcode_loading(self):
        self.gcode.cancel()
        self.gcode = None
        self.status = 'canceled'
        self.disable_generate_button()
        self.set_generate_button()
        self.set_progress_bar(0)


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

    #TODO:Better way
    def generate_gcode_filename(self):
        suggest_filename = ""
        filename = ""
        '''
        list = []
        if len(self.scene.models) == 1:
            filename = self.scene.models[0].filename
            suggest_filename = filename.split(".")
            suggest_filename = suggest_filename[0]
        else:
            #for m in self.scene.models:
            #    list.append(m.filename)
            suggest_filename = "mix"
        '''
        for m in self.scene.models:
            if m.isVisible:
                filename = m.filename
                break

        suggest_filename = filename.split(".")
        suggest_filename = suggest_filename[0]
        data = self.get_actual_printing_data()
        material_name = data['material']
        quality_name = data['quality']

        suggest_filename += "_" + material_name.upper() + "_" + quality_name.upper()

        return suggest_filename


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
        suggested_filename = self.generate_gcode_filename()
        data = self.view.save_gcode_file_dialog(suggested_filename)
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
        for path in data:
            self.import_model(path)

    def open_multipart_model(self):
        data = self.view.open_model_file_dialog()
        model_lst = []
        for path in data:
            model_lst.append(self.import_model(path, one_model=True))

        for m in model_lst:
            m.pos = model_lst[0].pos
            m.rot = model_lst[0].rot
            m.scale = model_lst[0].scale


    def import_model(self, path, one_model=False):
        self.view.statusBar().showMessage('Load file name: ' + path)
        model = ModelTypeStl().load(path)
        model.parent = self.scene
        self.scene.models.append(model)
        if self.settings['automatic_placing'] and not one_model:
            self.scene.automatic_models_position()
        self.scene.clear_history()
        self.scene.save_change(self.scene.models)
        self.update_scene()
        self.is_model_loaded = True
        return model
        #self.view.update_scene()

    def import_project(self, path):
        project_file = ProjectFile(self.scene, path)
        self.update_scene()

        #self.view.update_scene()

    def save_project(self, path):
        self.scene.check_models_name()
        project_file = ProjectFile(self.scene)
        project_file.save(path)
        self.scene_was_saved = True

    '''
    def open_asking_dialog(self, type):
        if type=="project":
    '''

    def update_scene(self):
        self.view.update_scene()
        if self.status in ['edit', 'canceled']:
            if self.scene.is_scene_printable():
                self.enable_generate_button()
            else:
                self.disable_generate_button()

    def update_firmware(self):
        #TODO:Add code for update of firmware
        pass

    def open_object_settings_dialog(self, object_id):
        object_settings = self.view.open_object_settings_dialog(object_id)

    def open_settings(self):
        temp_settings = self.view.open_settings_dialog()
        if not temp_settings['language'] == self.settings['language']:
            self.set_language(temp_settings['language'])
            self.show_message_on_status_bar(self.app.tr("Language change will take effect after application restart"))

        printer_settings = self.printing_parameters.get_printer_parameters(temp_settings['printer'])
        self.printer_number_of_materials = printer_settings['multimaterial']
        if self.printer_number_of_materials>1:
            self.view.set_multimaterial_gui_on(self.printer_number_of_materials)
        else:
            self.view.set_multimaterial_gui_off()

        self.settings = temp_settings

    def open_about(self):
        self.view.open_about_dialog()

    def generate_gcode(self):
        self.set_progress_bar(int((100. / 9.)))
        if self.scene.models:
            self.scene.save_whole_scene_to_one_stl_file(self.app_config.tmp_place + "tmp.stl")
            self.slicer_manager.slice()

    def gcode_generated(self):
        self.view.enable_save_gcode_button()

    def close(self):
        exit()

    def set_print_info_text(self, string):
        #print("Nejaky text ze Sliceru: " + string)
        string = string.split(' ')
        self.filament_use = string[0]
        #self.gcode.set_print_info_text(string[0])

    def scene_was_changed(self):
        if self.status == 'generating':
            self.cancel_generation()
        self.status = 'edit'
        self.scene.analyze_result_data_tmp = []
        self.set_generate_button()
        self.set_progress_bar(0.0)

    '''
    def set_model_view_mode(self):
        if self.status in ['generating']:
            pass
        elif self.status in ['loading_gcode']:
            #set progressbar
            self.set_progress_bar(0)
            #set generate button
            self.set_generate_button()

        self.render_status == 'model_view'
    '''

    def wheel_event(self, event):
        self.view.set_zoom(event.delta()/120)
        #self.view.statusBar().showMessage("Zoom = %s" % self.view.get_zoom())
        self.update_scene()
        #self.view.update_scene()


    def set_camera_move_function(self):
        self.camera_move=True
        self.camera_rotate=False

    def set_camera_rotation_function(self):
        self.camera_move = False
        self.camera_rotate = True
        self.cursor_over_object = False

    def set_camera_function_false(self):
        self.camera_move = False
        self.camera_rotate = False
        self.cursor_over_object = False

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


    #def get_active_tool(self):
    #    return None

    def is_some_tool_helper_under_cursor(self, object_id):
        if object_id == 0:
            return False
        for model in self.scene.models:
            if model.selected:
                if model.rotateXId == object_id:
                    model.scalenAxis = []
                    model.selected = True
                    model.rotationAxis = 'x'
                    self.tool = 'rotate'
                    return True
                elif model.rotateYId == object_id:
                    model.scalenAxis = []
                    model.selected = True
                    model.rotationAxis = 'y'
                    self.tool = 'rotate'
                    return True
                elif model.rotateZId == object_id:
                    model.scalenAxis = []
                    model.selected = True
                    model.rotationAxis = 'z'
                    self.tool = 'rotate'
                    return True
                elif model.scaleXId == object_id:
                    model.rotationAxis = []
                    model.selected = True
                    model.scaleAxis = 'x'
                    self.tool = 'scale'
                    return True
                elif model.scaleYId == object_id:
                    model.rotationAxis = []
                    model.selected = True
                    model.scaleAxis = 'y'
                    self.tool = 'scale'
                    return True
                elif model.scaleZId == object_id:
                    model.rotationAxis = []
                    model.selected = True
                    model.scaleAxis = 'z'
                    self.tool = 'scale'
                    return True
                elif model.scaleXYZId == object_id:
                    model.rotationAxis = []
                    model.selected = True
                    model.scaleAxis = 'XYZ'
                    self.tool = 'scale'
                    return True
                else:
                    model.rotationAxis = []
                    model.scalenAxis = []
                    #model.selected = False


    def set_active_tool_helper_by_id(self, object_id):
        pass


    @staticmethod
    def is_ctrl_pressed():
        #print("is_ctrl_pressed")
        modifiers = QtGui.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ControlModifier:
            return True
        else:
            return False

    def is_object_already_selected(self, object_id):
        print("is_object_already_selected")
        for model in self.scene.models:
            #object founded
            if model.id == object_id:
                print("Je model oznaceny: " + str(model.selected))
                if model.selected:
                    #object is selected
                    print("return True")
                    return True
                else:
                    #object is not selected
                    print("return False")
                    return False
        #No object with id in scene.models
        return None

    def unselect_objects_and_select_this_one(self, object_id):
        self.unselect_objects()
        one_selected = False
        for model in self.scene.models:
            #object founded
            if model.id == object_id:
                model.selected = True
                one_selected = True
                self.object_select_event_flag = True

        if one_selected:
            return True
        else:
            return False


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
                self.object_select_event_flag = True
                self.open_object_settings(object_id)
                return True
        return False



    def unselect_objects(self):
        #print("Unselect objects")
        for model in self.scene.models:
            model.selected = False

        if self.status in ['edit', 'canceled']:
            self.close_object_settings()

    def add_camera_position(self, vec):
        self.view.add_camera_position(vec)

    def check_rotation_axis(self, event):
        if self.settings['toolButtons']['rotateButton']:
            if self.find_object_and_rotation_axis_by_color(event):
                self.update_scene()
                #self.view.update_scene()

    def copy_selected_objects(self):
        self.scene.copy_selected_objects()

    def paste_selected_objects(self):
        self.scene.paste_selected_objects()

    def delete_selected_objects(self):
        self.scene.delete_selected_models()

    def do_function(self):
        self.view.glWidget.do_button.press_button()

    def undo_function(self):
        self.view.glWidget.undo_button.press_button()



    def key_press_event(self, event):
        key = event.key()
        if key in [Qt.Key_Delete, Qt.Key_Backspace] and self.render_status == 'model_view':
            self.delete_selected_objects()
            self.update_scene()
        elif key in [Qt.Key_C] and self.is_ctrl_pressed() and self.render_status == 'model_view':
            #print("Copy models")
            self.copy_selected_objects()
            self.update_scene()
        elif key in [Qt.Key_V] and self.is_ctrl_pressed() and self.render_status == 'model_view':
            #print("Paste models")
            self.paste_selected_objects()
            self.update_scene()
        elif key in [Qt.Key_Z] and self.is_ctrl_pressed() and self.render_status == 'model_view':
            #print("Undo pressed")
            self.unselect_tool_buttons()
            self.undo_function()
            #self.undo_button_pressed()
            self.update_scene()
        elif key in [Qt.Key_Y] and self.is_ctrl_pressed() and self.render_status == 'model_view':
            #print("Redo pressed")
            self.unselect_tool_buttons()
            self.do_function()
            #self.do_button_pressed()
            self.update_scene()
        elif key in [Qt.Key_R] and self.render_status == 'model_view':
            #print("R pressed ")
            if self.view.glWidget.rotateTool.is_pressed():
                self.unselect_tool_buttons()
            else:
                self.unselect_tool_buttons()
                self.view.glWidget.rotateTool.press_button()
            self.update_scene()
        elif key in [Qt.Key_S] and self.render_status == 'model_view':
            #print("S pressed ")
            if self.view.glWidget.scaleTool.is_pressed():
                self.unselect_tool_buttons()
            else:
                self.unselect_tool_buttons()
                self.view.glWidget.scaleTool.press_button()
            self.update_scene()
        elif key in [Qt.Key_A] and self.is_ctrl_pressed() and self.render_status == 'model_view':
            #print("A and ctrl pressed")
            self.select_all()
            self.update_scene()
        elif key in [Qt.Key_A] and self.render_status == 'model_view':
            #print("A pressed")
            self.unselect_tool_buttons()
            self.scene.automatic_models_position()
            self.update_scene()
        elif key in [Qt.Key_I] and self.is_ctrl_pressed() and self.render_status == 'model_view':
            #print("I and ctrl pressed ")
            self.invert_selection()
            self.update_scene()



    def mouse_double_click(self, event):
        pass

    def select_all(self):
        for m in self.scene.models:
            if m.isVisible:
                m.selected = True

    def invert_selection(self):
        for m in self.scene.models:
            if m.isVisible:
                m.selected = not m.selected

    '''
    def mouse_double_click(self, event):
        self.mouse_double_click_event_flag = True
        if self.render_status == 'model_view' and event.button() & QtCore.Qt.LeftButton:
            object_id = self.get_id_under_cursor(event)
            if object_id == 0 or self.is_some_tool_under_cursor(object_id):
                return
            else:
                self.open_object_settings(object_id)
    '''


    def mouse_press_event(self, event):
        #print("Mouse press event")
        self.clear_event_flag_status()
        self.mouse_press_event_flag = True

        newRayStart, newRayEnd = self.view.get_cursor_position(event)
        self.res_old = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
        #Je stisknuto prave tlacitko?
        if event.button() & QtCore.Qt.RightButton:
            self.set_camera_move_function()
        #Je stisknuto leve tlacitko?
        elif event.button() & QtCore.Qt.LeftButton:
            #Je kurzor nad nejakym objektem?
            if self.render_status == 'model_view' and self.status in ['edit', 'canceled']:
                object_id = self.get_id_under_cursor(event)
                if object_id == 0 and self.settings['toolButtons']['supportButton']:
                    if self.scene.actual_support:
                        self.scene.save_actual_support()
                elif object_id==0:
                    self.set_camera_rotation_function()
                else:
                    #Je pod kurzorem nejaky tool?
                    if self.is_some_tool_under_cursor(object_id):
                        #print("pod kurzorem je Tool")
                        #self.unselect_objects()
                        self.tool_press_event_flag = True
                        self.tool = self.get_tool_by_id(object_id)
                        for t in self.tools:
                            if not t == self.tool:
                                t.unpress_button()
                            else:
                                self.tool.press_button()
                        #tool.activate_tool()

                    #Je pod kurzorem nejaky tool helper?
                    elif self.is_some_tool_helper_under_cursor(object_id):
                        #print("tool helper under cursor")
                        self.tool_helper_press_event_flag = True
                        #self.set_active_tool_helper_by_id(object_id)
                        self.prepare_tool(event)

                    elif self.is_object_already_selected(object_id) and self.is_ctrl_pressed():
                        #print("object already selected and ctrl pressed")
                        self.object_select_event_flag = True
                        self.cursor_over_object = True
                        self.unselect_object(object_id)
                    elif self.is_ctrl_pressed():
                        #print("ctrl pressed")
                        self.select_object(object_id)
                        self.cursor_over_object = True
                    elif self.is_object_already_selected(object_id) and self.is_some_tool_active():
                        #print("object already selected and tool placeonface is on")
                        self.tool=self.get_active_tool()
                        self.prepare_tool(event)
                        self.cursor_over_object = True
                    elif self.is_object_already_selected(object_id):
                        #print("object already selected")
                        pass
                        self.cursor_over_object = True
                    else:
                        #print("else")
                        self.unselect_objects()
                        self.select_object(object_id)
                        self.cursor_over_object = True

                    #print("Aktualni tool je: " + self.tool)
                    self.tool = self.get_active_tool()
                    #Je objekt oznaceny?
                    '''
                    elif self.is_ctrl_pressed():
                        if self.is_object_already_selected(object_id):
                            self.unselect_object(object_id)
                        else:
                            self.select_object(object_id)
                    '''
                    #elif self.is_object_already_selected(object_id):


                    '''
                    elif self.unselect_objects_and_select_this_one(object_id):
                        print("Klikani na objekt")
                        #nastav funkci na provedeni toolu

                        self.tool = self.get_active_tool()
                        print("Aktualni tool je " + self.tool)

                        #TODO:add function get_active_tool(self) return class tool
                        #tool = self.get_toolsactive_tool()
                        #TODO:add function do(self) to class tool
                        self.prepare_tool(event)
                    else:
                        #select object
                        print("Else:")
                        self.unselect_objects()
                        self.select_object(object_id)
                    '''


            else:
                #print("Jiny status nez model_view")
                self.unselect_objects()
                self.set_camera_rotation_function()
        self.update_scene()
        #self.view.update_scene()


    def is_some_tool_active(self):
        for tool in self.tools:
            if tool.is_pressed() and tool.tool_name=='placeonface':
                return True

        return False

    #def get_active_tool(self):
    #    for tool in self.tools:
    #        if tool.is_pressed():
    #            return tool.tool_name


    def prepare_tool(self, event):
        #print("prepare tool")
        if self.tool == 'rotate':
            for model in self.scene.models:
                if model.selected:
                    #newRayStart, newRayEnd = self.view.get_cursor_position(event)
                    #self.origin_rotation_point = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
                    #self.res_old = self.origin_rotation_point
                    self.origin_rotation_point = numpy.array([1.,0.,0.])
                    self.origin_rotation_point += model.pos
                    self.origin_rotation_point[2] = 0.
                    self.res_old = self.origin_rotation_point
                    self.old_angle = model.rot[2]
            #self.view.glWidget.oldHitPoint = numpy.array([0., 0., 0.])
            #self.view.glWidget.hitPoint = numpy.array([0., 0., 0.])


        elif self.tool == 'placeonface':
            #print("inside placeonface")
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
                        #print("Nalezen objekt " + str(model))
        elif self.tool == 'scale':
            ray_start, ray_end = self.view.get_cursor_position(event)

            for model in self.scene.models:
                if model.selected:
                    pos = deepcopy(model.pos)
                    pos[2] = 0.
                    self.original_scale_point = numpy.array(sceneData.intersection_ray_plane(ray_start, ray_end))
                    self.original_scale = numpy.linalg.norm(self.original_scale_point - pos)
                    self.last_l = 0.0





    def mouse_move_event(self, event):
        #print("Mouse move event")
        self.mouse_move_event_flag = True
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        #diff = numpy.linalg.norm(numpy.array([dx, dy]))

        if self.camera_move and self.mouse_press_event_flag:
            #print("camera move")
            camStart, camDir, camUp, camRight = self.view.get_camera_direction(event)
            right_move = -0.025*dx * camRight
            up_move = 0.025*dy * camUp

            move_vector = right_move + up_move
            self.add_camera_position(move_vector)

        elif self.camera_rotate and self.mouse_press_event_flag:
            #print("camera rotate")
            self.view.set_x_rotation(self.view.get_x_rotation() + 8 * dy)
            self.view.set_z_rotation(self.view.get_z_rotation() + 8 * dx)
            #camera_pos, direction, _, _ = self.view.get_camera_direction(event)
            #self.scene.camera_vector = direction - camera_pos
        #Check if some tool helper is pressed after that decide which tool is selected and
        #make some change, other way move
        elif self.tool_helper_press_event_flag:
            if self.tool == 'rotate':
                #print("rotate function")
                newRayStart, newRayEnd = self.view.get_cursor_position(event)
                res = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
                if res is not None:
                    res_new = res - self.res_old
                    for model in self.scene.models:
                        if model.selected:
                            pos = deepcopy(model.pos)
                            pos[2] = 0.

                            #New
                            new_vec = res - pos
                            #self.view.glWidget.hitPoint = deepcopy(new_vec)
                            new_vect_leng = numpy.linalg.norm(new_vec)
                            new_vec /= new_vect_leng

                            old_vec = self.res_old - pos
                            #self.view.glWidget.oldHitPoint = deepcopy(old_vec)
                            old_vec /= numpy.linalg.norm(old_vec)

                            cos_ang = numpy.dot(old_vec, new_vec)
                            cross = numpy.cross(old_vec, new_vec)

                            neg = numpy.dot(cross, numpy.array([0., 0., 1.]))
                            sin_ang = numpy.linalg.norm(cross) * numpy.sign(neg) * -1.

                            alpha = numpy.arctan2(sin_ang, cos_ang)

                            radius = model.boundingSphereSize

                            if radius < 2.5:
                                radius = 2.5

                            if new_vect_leng >= radius:
                                model.set_rot(model.rot[0], model.rot[1], alpha, False, False, False)
                            else:
                                alpha_new = numpy.degrees(alpha) // 45
                                model.set_rot(model.rot[0], model.rot[1], alpha_new*(numpy.pi*.25), False, False, False)

                            #self.view.update_object_settings(model.id)
                            self.view.update_rotate_widgets(model.id)
                            self.scene_was_changed()
            elif self.tool == 'scale':
                # print("scale function")
                ray_start, ray_end = self.view.get_cursor_position(event)
                # camera_pos, direction, _, _ = self.view.get_camera_direction(event)

                for model in self.scene.models:
                    if model.selected:
                        pos = deepcopy(model.pos)
                        pos[2] = 0.
                        new_scale_point = numpy.array(sceneData.intersection_ray_plane(ray_start, ray_end))
                        new_scale_vect = new_scale_point - pos

                        l = numpy.linalg.norm(new_scale_vect)
                        l -= .5

                        origin_size = deepcopy(model.size_origin)
                        origin_size[2] = 0.
                        origin_size *= .5

                        new_scale = l / numpy.linalg.norm(origin_size)
                        # print("Nova velikost scalu: " + str(new_scale))

                        model.set_scale_abs(new_scale, new_scale, new_scale)
                        # model.set_scale(new_scale)
                        self.last_l = new_scale

                        self.view.update_scale_widgets(model.id)
                        self.scene_was_changed()
        #Move function
        elif self.settings['toolButtons']['supportButton']:
            print("support function")
            newRayStart, newRayEnd = self.view.get_cursor_position(event)
            res = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
            if res is not None:
                self.scene.calculate_support(res)

        elif not self.tool_helper_press_event_flag \
                and self.mouse_press_event_flag \
                and self.cursor_over_object:
            print("move function")
            newRayStart, newRayEnd = self.view.get_cursor_position(event)
            res = sceneData.intersection_ray_plane(newRayStart, newRayEnd)
            if res is not None:
                res_new = res - self.res_old
                for model in self.scene.models:
                    if model.selected:
                        model.set_move(res_new)
                        #self.view.update_object_settings(model.id)
                        self.view.update_position_widgets(model.id)
                        self.scene_was_changed()
                self.res_old = res

        else:
            #print("Mouse move event else vetev")
            if self.render_status == 'model_view':
                object_id = self.get_id_under_cursor(event)
                #TOOLs hover effect
                if object_id > 0:
                    #Je pod kurzorem nejaky tool?
                    for tool in self.tools:
                        if tool.id == object_id:
                            tool.mouse_is_over(True)
                            self.view.glWidget.setToolTip(tool.tool_tip)
                        else:
                            tool.mouse_is_over(False)

                    #if self.settings['toolButtons']['rotateButton']:
                    #    self.select_tool_helper_by_id(object_id)
                        #for tool_helper in self.get_tools_helpers_id(1,0):
                        #    if tool_helper == object_id:
                else:
                    #TODO:Disable tooltip
                    self.view.glWidget.setToolTip("")
                    for tool in self.tools:
                        tool.mouse_is_over(False)


        self.last_pos = QtCore.QPoint(event.pos())
        self.update_scene()
        #self.view.update_scene()

    def select_tool_helper(self, event):
        object_id = self.get_id_under_cursor(event)
        if object_id > 0:
            self.select_tool_helper_by_id(object_id)

    def select_tool_helper_by_id(self, object_id):
        for m in self.scene.models:
            if m.isVisible:
                if object_id == m.rotateZId:
                    m.rotationAxis = "Z"
                    m.scaleAxis = ""
                elif object_id == m.scaleXYZId:
                    m.scaleAxis = "XYZ"
                    m.rotationAxis = ""
                else:
                    m.rotationAxis = ""
                    m.scaleAxis = ""

    #def support_tool_button_pressed(self):
    #    self.tool = "support"

    def organize_button_pressed(self):
        self.scene.automatic_models_position()

    def get_active_tool(self):
        for tool in self.tools:
            if tool.pressed:
                #print("Tool name: " + str(tool.tool_name))
                return tool.tool_name
        return 'move'

    def mouse_release_event(self, event):
        models_list = []
        #print("Mouse releas event")
        self.mouse_release_event_flag = True
        self.set_camera_function_false()
        if self.tool in ['move', 'rotate', 'scale', 'placeonface']:
            self.old_angle = 0.0
            for model in self.scene.models:
                if model.selected:
                    model.update_min_max()
                    if not self.tool == 'scale':
                        model.recalc_bounding_sphere()
                    models_list.append(model)
            if models_list and self.mouse_move_event_flag:
                self.scene.save_change(self.scene.models)
                #self.scene.save_change(models_list)
        self.tool = ''
        self.res_old = numpy.array([0.,0.,0.])

        if event.button() & QtCore.Qt.LeftButton and self.mouse_press_event_flag and\
                self.mouse_release_event_flag and self.mouse_move_event_flag == False and\
                self.object_select_event_flag==False and self.tool_press_event_flag == False:
            #print("Podminky splneny")
            self.clear_event_flag_status()
            self.unselect_objects()
        self.update_scene()

    def open_object_settings(self, object_id):
        self.set_basic_settings()
        self.view.create_object_settings_menu(object_id)

    def close_object_settings(self):
        self.set_basic_settings()
        self.view.close_object_settings_panel()

    def set_printable(self, is_printable):
        self.scene.printable = is_printable
        if is_printable == False:
            #print("Disable genrate button")
            self.disable_generate_button()
        else:
            #print("Enable genrate button")
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
                #print("Tady bych to necekal")
                model.selected = False

        if not nSelected:
            return False

        #print("A tady taky ne")
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
                #print("Tady to je!!!")
                model.selected = not model.selected
                return True

    def reset_scene(self):
        self.scene.clear_scene()
        self.update_scene()
        self.is_model_loaded = False
        #self.view.update_scene(True)

    def clear_gui(self):
        self.view.reinit()

    def reset(self):
        #reset render mode
        self.scene_was_changed()
        self.set_model_edit_view()
        #reset gcode data
        self.clear_gcode()
        #reset gui
        self.clear_gui()
        self.reset_scene()

    def import_image(self, path):
        #TODO:Add importing of image(just plane with texture?)
        pass

    def undo_button_pressed(self):
        #print("Undo")
        self.clear_tool_button_states()
        self.scene.make_undo()
        self.update_scene()

    def do_button_pressed(self):
        #print("Do")
        self.clear_tool_button_states()
        self.scene.make_do()
        self.update_scene()

    def select_button_pressed(self):
        self.clear_tool_button_states()
        self.settings['toolButtons']['selectButton'] = True
        self.update_scene()
        #self.view.update_scene()

    def move_button_pressed(self):
        if self.settings['toolButtons']['moveButton']:
            self.settings['toolButtons']['moveButton'] = not(self.settings['toolButtons']['moveButton'])
        else:
            self.clear_tool_button_states()
            self.settings['toolButtons']['moveButton'] = True
        self.update_scene()
        #self.view.update_scene()

    def rotate_button_pressed(self):
        if self.settings['toolButtons']['rotateButton']:
            self.settings['toolButtons']['rotateButton'] = not(self.settings['toolButtons']['rotateButton'])
        else:
            self.clear_tool_button_states()
            self.settings['toolButtons']['rotateButton'] = True
        self.update_scene()
        #self.view.update_scene()

    def support_button_pressed(self):
        if self.settings['toolButtons']['supportButton']:
            self.settings['toolButtons']['supportButton'] = not(self.settings['toolButtons']['supportButton'])
        else:
            self.clear_tool_button_states()
            self.settings['toolButtons']['supportButton'] = True
        self.update_scene()


    def scale_button_pressed(self):
        if self.settings['toolButtons']['scaleButton']:
            self.settings['toolButtons']['scaleButton'] = not(self.settings['toolButtons']['scaleButton'])
        else:
            self.clear_tool_button_states()
            self.settings['toolButtons']['scaleButton'] = True
        self.update_scene()
        #self.view.update_scene()

    def place_on_face_button_pressed(self):
        #TODO:Add new tool
        pass

    def clear_tool_button_states(self):
        self.settings['toolButtons'] = {a: False for a in self.settings['toolButtons']}

    def slicing_message(self, string_in):
        #Translation of messages from slicing engine

        translation_table = {'Generating perimeters': self.view.tr('Generating perimeters'),
                             'Processing triangulated mesh': self.view.tr('Processing triangulated mesh'),
                             'Infilling layers': self.view.tr('Infilling layers'),
                             'Preparing infill': self.view.tr('Preparing infill'),
                             'Generating skirt': self.view.tr('Generating skirt'),
                             'Exporting G-code to': self.view.tr('Exporting G-code to'),
                             'Done. Process took': self.view.tr('Done. Process took')
                             }

        string_in_str = str(string_in)
        if string_in_str in translation_table:
            string_out = translation_table[string_in_str]
        else:
            string_out = string_in

        self.show_message_on_status_bar(string_out)


    def show_message_on_status_bar(self, string):
        self.view.statusBar().showMessage(string)

    def open_clear_scene_and_load_gcode_file(self):
        ret = self.view.show_clear_scene_and_load_gcode_file_dialog()
        if ret == QtGui.QMessageBox.Yes:
            self.scene.clear_scene()
            return True
        elif ret == QtGui.QMessageBox.No:
            return False

    def open_cancel_gcode_preview_dialog(self):
        ret = self.view.show_open_cancel_gcode_preview_dialog()
        if ret == QtGui.QMessageBox.Yes:
            self.status = 'edit'
            self.set_model_edit_view()
            return True
        elif ret == QtGui.QMessageBox.No:
            return False


    def open_file(self, url):
        '''
        function for resolve which file type will be loaded
        '''
        if self.status in ['generating']:
            if not self.open_cancel_generating_dialog():
                return
        elif self.status in ['loading_gcode']:
            if not self.open_cancel_gcode_reading_dialog():
                return
        elif self.status in ['generated']:
            if not self.open_cancel_gcode_preview_dialog():
                return



        #self.view.statusBar().showMessage('Load file name: ')

        #TODO:Why?
        #if url[0] == '/' and self.app_config.system_platform in ['Windows']:
        #    url = url[1:]

        urlSplited = url.split('.')
        if len(urlSplited)==2:
            fileEnd = urlSplited[1]
        elif len(urlSplited)>2:
            fileEnd = urlSplited[-1]
        else:
            fileEnd=''

        if fileEnd in ['stl', 'STL', 'Stl']:
            #print('import model')
            self.import_model(url)
        elif fileEnd in ['prus', 'PRUS']:
            #print('open project')

            self.open_project_file(url)
        elif fileEnd in ['jpeg', 'jpg', 'png', 'bmp']:
            #print('import image')
            self.import_image(url)
        elif fileEnd in ['gcode']:
            if self.is_something_to_save():
                if not self.open_clear_scene_and_load_gcode_file():
                    return
            self.read_gcode(url)




