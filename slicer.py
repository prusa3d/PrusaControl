# -*- coding: utf-8 -*-
import logging
import os
from ConfigParser import ConfigParser
from abc import ABCMeta, abstractmethod


import platform
import subprocess
from copy import deepcopy

from PyQt4.QtCore import QObject, QThread, pyqtSignal


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


class Slic3rEngineRunner(QObject):
    '''
    This is just connector to console version of Slic3r software
    first version
    '''
    step_increased = pyqtSignal(int)
    filament_info = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, controller):
        super(Slic3rEngineRunner, self).__init__()
        self.is_running = True
        self.controller = controller

        system_platform = platform.system()
        if system_platform in ['Linux']:
            self.slicer_place = ['../Slic3r/bin/slic3r']
            #self.slicer_place = './tools/Slic3r-Lite/slic3r'
        elif system_platform in ['Darwin']:
            self.slicer_place = ['../MacOS/Slic3r']
        elif system_platform in ['Windows']:
            self.slicer_place = ['tools\\Slic3r-Lite\\perl5.22.1.exe', 'slic3r.pl']
        else:
            self.slicer_place = ['slic3r']

        print(self.slicer_place)

        self.data = {}

        self.step_max = 8
        self.step = 0

    def set_data(self, data):
        self.data = data

    def translate_dictionary(self, old, update):
        translation_table = [
            ['fill_density', 'infill', self.percent_transform],
            ['brim_width', 'brim', self.boolean_transform],
            ['support_material', 'support', self.boolean_transform]
        ]
        for i in translation_table:
            old[i[0]] = i[2](update[i[1]])
        return old

    def percent_transform(self, in_value):
        return "%s" % str(in_value) + '%'

    def boolean_transform(self, in_value):
        return "%s" % str(int(in_value))

    def save_configuration(self, filename):
        actual_printing_data = self.controller.get_actual_printing_data()
        material_printing_data = self.controller.get_printing_parameters_for_material_quality(actual_printing_data['material'], actual_printing_data['quality'])
        new_parameters = self.translate_dictionary(material_printing_data, actual_printing_data)
        new_config = ConfigParser()
        new_config.add_section('settings')
        for i in new_parameters:
            new_config.set('settings', i, new_parameters[i])

        #write ini file
        with open(filename, 'w') as ini_file:
            new_config.write(ini_file)

    def slice(self):
        self.save_configuration(self.controller.tmp_place + 'prusacontrol.ini')

        process = subprocess.Popen(self.slicer_place + [self.controller.tmp_place + 'tmp.stl', '--load',
                                    self.controller.tmp_place + 'prusacontrol.ini', '--output',
                                    self.controller.tmp_place + 'out.gcode'], stdout=subprocess.PIPE)
        self.check_progress(process)

    def check_progress(self, process):
        #for line in iter(process.stdout.readline, ''):
        while self.step <= 8 and self.is_running is True:
            line = process.stdout.readline()
            self.step += 1
            if not line:
                break
            print(line.rstrip())
            self.step_increased.emit(int(((10. / 8.) * self.step) * 10))
            if self.step == 8:
                filament_str = line.rsplit()
                filament_str = filament_str[2:4]
                filament_str = str(filament_str[0] + ' ' + filament_str[1])
                self.filament_info.emit(filament_str)
                self.finished.emit()
                break

    def end(self):
        self.end_callback()

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
        self.slice_engine = None

    def slice(self):
        data = {'material': 'PLA',
                'quality': 'best',
                'scene': self.controller.scene
                }

        #self.controller.set_cancel_button()
        self.slice_thread = QThread()
        self.slice_engine = Slic3rEngineRunner(self.controller)
        self.slice_engine.moveToThread(self.slice_thread)
        self.slice_engine.set_data(data)
        self.slice_thread.started.connect(self.slice_engine.slice)
        self.slice_engine.finished.connect(self.thread_ended)
        self.slice_engine.filament_info.connect(self.controller.set_print_info_text)
        self.slice_engine.step_increased.connect(self.controller.set_progress_bar)

        self.slice_thread.start()

    def cancel(self):
        logging.debug("Thread canceling")
        if self.slice_engine and self.slice_thread:
            self.slice_engine.is_running = False
            self.slice_thread.quit()
            self.slice_thread.wait()
            self.controller.status = 'canceled'
            self.controller.set_generate_button()
            self.controller.set_progress_bar(0.0)

    def thread_ended(self):
        self.slice_thread.quit()
        self.controller.set_save_gcode_button()
        self.controller.status = 'generated'
