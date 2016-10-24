# -*- coding: utf-8 -*-
import logging
import os
from ConfigParser import ConfigParser
from abc import ABCMeta, abstractmethod


import platform
import subprocess
from copy import deepcopy

import cStringIO
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

    def __init__(self, controller):
        super(Slic3rEngineRunner, self).__init__()
        self.is_running = True
        self.controller = controller

        system_platform = platform.system()
        if system_platform in ['Linux']:
            self.slicer_place = ['/home/tibor/dev/Slic3r/bin/slic3r']
            #self.slicer_place = './tools/Slic3r-Lite/slic3r'
        elif system_platform in ['Darwin']:
            self.slicer_place = ['../MacOS/Slic3r']
        elif system_platform in ['Windows']:
            self.slicer_place = ['tools\\Slic3r-Lite\\perl5.22.1.exe', 'tools\\Slic3r-Lite\\slic3r.pl']
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
            ['support_material_buildplate_only', 'support_build_plate', self.support2_transform]
        ]
        for i in translation_table:
            old[i[0]] = i[2](update[i[1]])
        return old

    def percent_transform(self, in_value):
        return "%s" % str(in_value) + '%'

    def boolean_transform(self, in_value):
        return "%s" % str(int(in_value))

    def support1_transform(self, in_value):
        if in_value == "None":
            return "0"
        elif in_value == "Build plate only":
            return "1"
        elif in_value == "Everywhere":
            return "1"
        else:
            return "0"
        return "0"

    def support2_transform(self, in_value):
        if in_value == "None":
            return "0"
        elif in_value == "Build plate only":
            return "1"
        elif in_value == "Everywhere":
            return "0"
        else:
            return "0"
        return "0"


    def save_configuration(self, filename):
        actual_printing_data = self.controller.get_actual_printing_data()
        for i in actual_printing_data:
            if i in ['brim', 'support_on_off', 'support_build_plate'] and actual_printing_data[i]==True:
                self.step_max+=1

        #material_printing_data = self.controller.get_printing_parameters_for_material_quality(actual_printing_data['material'], actual_printing_data['quality'])
        material_printing_data = self.controller.printing_parameters.get_actual_settings(self.controller.actual_printer, self.controller.settings['printer_type'], actual_printing_data['material'], actual_printing_data['quality'])
        print("All settings: " + str(material_printing_data))
        new_parameters = self.translate_dictionary(material_printing_data, actual_printing_data)
        new_config = ConfigParser()
        new_config.add_section('settings')
        for i in new_parameters:
            new_config.set('settings', i, new_parameters[i])

        #write ini file
        with open(filename, 'w') as ini_file:
            fake_file = cStringIO.StringIO()
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
        while self.step <= self.step_max and self.is_running is True:
            line = self.process.stdout.readline()
            self.step += 1
            if not line:
                break
            self.step_increased.emit(int(((10. / (self.step_max+1)*1.) * (self.step + 1)) * 10))
            if self.step == self.step_max:
                filament_str = line.rsplit()
                filament_str = filament_str[2:4]
                filament_str = str(filament_str[0] + ' ' + filament_str[1])
                self.filament_info.emit(filament_str)
                self.finished.emit()
                break
            else:
                text = line.rsplit()[1:]
                if text[0] == 'Exporting':
                    text = text[:2]
                self.send_message.emit(" ".join(text))

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
        self.slice_thread = QThread()
        #TODO:Make it universal(for other slice engines)
        self.slice_engine = Slic3rEngineRunner(self.controller)
        self.slice_engine.moveToThread(self.slice_thread)
        self.slice_thread.started.connect(self.slice_engine.slice)
        self.slice_engine.finished.connect(self.thread_ended)
        self.slice_engine.filament_info.connect(self.controller.set_print_info_text)
        self.slice_engine.step_increased.connect(self.controller.set_progress_bar)
        self.slice_engine.send_message.connect(self.controller.show_message_on_status_bar)

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

