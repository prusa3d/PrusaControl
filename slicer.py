# -*- coding: utf-8 -*-
import io
import logging
import os
import configparser
from abc import ABCMeta, abstractmethod


import platform
import subprocess
from copy import deepcopy

from io import StringIO

import signal
from PyQt4.QtCore import QObject, QThread, pyqtSignal

from gcode import GCode


class SlicerEngineAbstract():
    '''
    SlicerEngineAbstract is abstract class patern for others SlicerEngines
    '''
    __metaclass__ = ABCMeta

    @abstractmethod
    def slice(self):
        pass

    @abstractmethod
    def set_data(self, data):
        pass

    @abstractmethod
    def get_version(self):
        pass


#TODO:This is wrong design,
class Slic3rEngineRunner(QObject):
    '''
    This is just connector to console version of Slic3r software
    first version
    '''
    step_increased = pyqtSignal(int)
    filament_info = pyqtSignal(str)
    finished = pyqtSignal()
    send_message = pyqtSignal(str)
    send_gcodedata = pyqtSignal(GCode)

    def __init__(self, controller):
        super(Slic3rEngineRunner, self).__init__()
        self.is_running = True
        self.controller = controller

        self.gcode = GCode(self.controller.app_config.tmp_place + 'out.gcode', self.controller, None, None)

        system_platform = platform.system()
        if system_platform in ['Linux']:
            self.slicer_place = ['/home/tibor/dev/Slic3r/bin/slic3r']
            #self.slicer_place = './tools/Slic3r-Lite/slic3r'
        elif system_platform in ['Darwin']:
            self.slicer_place = ['../MacOS/Slic3r']
        elif system_platform in ['Windows']:
            self.slicer_place = ['tools\\Slic3r-Lite\\slic3r-console.exe']
        else:
            self.slicer_place = ['slic3r']

        #print(self.slicer_place)

        self.step_max = 8
        self.step = 0


    def translate_dictionary(self, old, update):
        translation_table = [
            ['fill_density', 'infill', self.percent_transform],
            ['brim_width', 'brim', self.boolean_transform],
            #['support_material', 'support', self.boolean_transform]
            ['support_material', 'support_on_off', self.support1_transform],
            ['support_material_buildplate_only', 'support_build_plate', self.support2_transform],
            ['overhangs', 'overhangs', self.support3_transform]
        ]
        for i in translation_table:
            old[i[0]] = i[2](update[i[1]])
        return old

    def percent_transform(self, in_value):
        return "%s" % str(in_value) + '%'

    def boolean_transform(self, in_value):
        return "%s" % str(int(in_value)*10)

    def support1_transform(self, in_value):
        if in_value == 0:   #None
            return "0"
        elif in_value == 1: #Build plate only
            return "1"
        elif in_value == 2: #Everywhere
            return "1"
        else:
            return "0"
        return "0"

    def support2_transform(self, in_value):
        if in_value == 0:   #None
            return "0"
        elif in_value == 1: #Build plate only
            return "1"
        elif in_value == 2: #Everywhere
            return "0"
        else:
            return "0"
        return "0"

    def support3_transform(self, in_value):
        if in_value == 0:   #None
            return "0"
        elif in_value == 1: #Build plate only
            return "1"
        elif in_value == 2: #Everywhere
            return "1"
        else:
            return "1"
        return "0"


    def save_configuration(self, filename):
        actual_printing_data = self.controller.get_actual_printing_data()
        for i in actual_printing_data:
            if i in ['brim', 'support_on_off'] and actual_printing_data[i]==True:
                self.step_max+=1

        #material_printing_data = self.controller.get_printing_parameters_for_material_quality(actual_printing_data['material'], actual_printing_data['quality'])
        material_printing_data = self.controller.printing_parameters.get_actual_settings(self.controller.actual_printer, self.controller.settings['printer_type'], actual_printing_data['material'], actual_printing_data['quality'])
        #print("All settings: " + str(material_printing_data))
        new_parameters = self.translate_dictionary(material_printing_data, actual_printing_data)
        new_config = configparser.RawConfigParser()
        new_config.add_section('settings')
        #new_config.set('settings', i, new_parameters)
        for i in new_parameters:
            new_config.set('settings', i, new_parameters[i])

        #write ini file
        with open(filename, 'w') as ini_file:
            fake_file = io.StringIO()
            new_config.write(fake_file)
            ini_file.write(fake_file.getvalue()[11:])


    def slice(self):
        self.save_configuration(self.controller.app_config.tmp_place + 'prusacontrol.ini')

        self.process = subprocess.Popen(self.slicer_place + [self.controller.app_config.tmp_place + 'tmp.stl', '--load',
                                    self.controller.app_config.tmp_place + 'prusacontrol.ini', '--output',
                                    self.controller.app_config.tmp_place + 'out.gcode', '--dont-arrange'],
                                   stdout=subprocess.PIPE)
        self.check_progress()

    def kill(self):
        self.process.kill()

    def check_progress(self):
        self.step = 1
        while self.is_running is True:
            self.step+=1
            if self.process.returncode == -signal.SIGSEGV:
                self.send_message.emit("Slic3r engine crash")
                break
            line = str(self.process.stdout.readline(), 'utf-8')
            parsed_line = line.rsplit()
            if not line:
                continue
            if 'Done.' in parsed_line[0]:
                self.step_increased.emit(95)
                self.send_message.emit("Generating G-code preview")
                self.gcode.read_in_realtime()
                self.send_gcodedata.emit(self.gcode)
                self.send_message.emit("")
            elif 'Filament' in parsed_line[0] and 'required:' in parsed_line[1]:
                filament_str = str(parsed_line[2] + ' ' + parsed_line[3])
                print(filament_str)
                self.filament_info.emit(filament_str)
                self.finished.emit()
                self.step_increased.emit(100)
                break
            else:
                text = line.rsplit()[1:]
                if text[0] == 'Exporting':
                    text = text[:2]
                self.send_message.emit(" ".join(text))
            self.step_increased.emit(int((self.step / 11.) * 100))

    def end(self):
        self.end_callback()

    def get_version(self):
        version_process = subprocess.Popen(self.slicer_place + ["--version"], stdout=subprocess.PIPE)
        version_info = version_process.stdout.readline()
        return version_info

class CuraEngine(SlicerEngineAbstract):
    '''
    This is just connector to console version of Slic3r software
    first version
    '''
    pass

class OwnSlicerEngine(SlicerEngineAbstract):
    '''
    PrusaResearch slicer engine, designed for their printers
    Future
    '''
    pass


class SlicerEngineManager(object):
    '''
    SlicerEngineManager is class designed for managing slicers engine and prepare parameters
    '''
    def __init__(self, controller):
        self.controller = controller
        self.slice_thread = None
        self.slice_engine = Slic3rEngineRunner(self.controller)


    def slice(self):
        self.slice_thread = QThread()
        #TODO:Make it universal(for other slice engines)
        self.slice_engine = Slic3rEngineRunner(self.controller)
        self.slice_engine.moveToThread(self.slice_thread)
        self.slice_thread.started.connect(self.slice_engine.slice)
        self.slice_engine.finished.connect(self.thread_ended)
        self.slice_engine.filament_info.connect(self.controller.set_print_info_text)
        self.slice_engine.step_increased.connect(self.controller.set_progress_bar)
        self.slice_engine.send_message.connect(self.controller.slicing_message)
        self.slice_engine.send_gcodedata.connect(self.controller.set_gcode_instance)

        self.slice_thread.start()

    def cancel(self):
        logging.debug("Thread canceling")
        if self.slice_engine and self.slice_thread:
            self.slice_engine.is_running = False
            self.slice_engine.kill()
            self.slice_thread.quit()
            self.slice_thread.wait()
            self.controller.status = 'canceled'
            self.controller.set_generate_button()
            self.controller.set_progress_bar(0.0)

    def thread_ended(self):
        self.slice_thread.quit()
        #TODO: add function to read gcode
        self.controller.scene_was_sliced()


    def get_version(self):
        return self.slice_engine.get_version()

