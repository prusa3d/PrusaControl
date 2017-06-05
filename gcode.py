# -*- coding: utf-8 -*-
import cProfile
import time
#from fastnumbers import fast_float
from collections import defaultdict
from collections import deque
from copy import deepcopy
from pprint import pprint
import os

import numpy as np
from PyQt4.QtCore import QFile
from PyQt4.QtCore import QIODevice
from PyQt4.QtCore import QObject
from PyQt4.QtCore import QTextStream
from PyQt4.QtCore import QThread
from PyQt4.QtCore import pyqtSignal


#Mesure
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print('%s function took %0.3f ms' % (f.__name__, (time2-time1)*1000.0))
        return ret
    return wrap

class GCode(object):

    def __init__(self, filename, controller, done_loading_callback, done_writing_callback):
        self.controller = controller
        self.done_loading_callback = done_loading_callback
        self.writing_done_callback = done_writing_callback
        self.data = {}
        self.all_data = []
        self.data_keys = set()
        self.color_change_data = []
        self.actual_z = '0.0'
        self.speed = 0.0
        self.z_hop = False
        self.last_point = np.array([0.0, 0.0, 0.0])
        self.actual_point = [0.0, 0.0, 0.0]

        self.printing_time = 0.0
        self.filament_length = 0.0
        #print("Filename type: " + str(type(filename)))
        #print("Filename: " + filename)
        #if type(filename)==:
        #self.filename = u'c:\\models\\super mega testovací Jindřich šložka čěýáéůú\\anubis_PLA_OPTIMAL.gcode'
        self.filename = filename

        self.is_loaded = False

        self.gcode_parser = GcodeParserRunner(controller, self.filename)
        self.gcode_parser_thread = QThread()

        self.gcode_copy = GcodeCopyRunner(self.filename, "", color_change_lst=self.color_change_data)
        self.gcode_copy_thread = QThread()


    def cancel_parsing_gcode(self):
        #print("Cancel presset")
        if self.gcode_parser and self.gcode_parser_thread and self.gcode_parser_thread.isRunning():
            self.gcode_parser.is_running = False
            self.gcode_parser_thread.quit()
            self.gcode_parser_thread.wait()
            self.is_loaded = False
            self.data = {}
            self.all_data = []
            self.data_keys = []
        self.controller.set_progress_bar(0)

    def cancel_writing_gcode(self):
        #print("Cancel writing gcode")
        if self.gcode_copy and self.gcode_copy_thread and self.gcode_copy_thread.isRunning():
            self.gcode_copy.quit()
            self.gcode_copy_thread.wait()

    def get_first_extruding_line_number_of_gcode_for_layers(self, layers_keys_lst):
        lines_number = []
        for i in layers_keys_lst:
            line = self.data[i]
            for o in line:
                _a, _b, type, _speed, _extr, line_n = o
                if 'E' in type:
                    lines_number.append(line_n)
                    break

        return lines_number

    def read_in_thread(self, update_progressbar_function, after_done_function):
        #print("reading in thread")
        self.gcode_parser.moveToThread(self.gcode_parser_thread)
        self.done_loading_callback = after_done_function

        # connect all signals to thread class
        self.gcode_parser_thread.started.connect(self.gcode_parser.load_gcode_file)
        #self.gcode_parser_thread.started.connect(self.gcode_parser.load_gcode_file_with_profile)
        # connect all signals to parser class
        self.gcode_parser.finished.connect(self.set_finished_read)
        self.gcode_parser.set_update_progress.connect(update_progressbar_function)
        self.gcode_parser.set_data_keys.connect(self.set_data_keys)
        self.gcode_parser.set_data.connect(self.set_data)
        self.gcode_parser.set_all_data.connect(self.set_all_data)
        self.gcode_parser.set_printing_time.connect(self.set_printig_time)

        self.gcode_parser_thread.start()


    def read_in_realtime(self):
        self.gcode_parser.set_data_keys.connect(self.set_data_keys)
        self.gcode_parser.set_data.connect(self.set_data)
        self.gcode_parser.set_all_data.connect(self.set_all_data)
        self.gcode_parser.set_printing_time.connect(self.set_printig_time)

        self.gcode_parser.load_gcode_file()

        self.is_loaded = True


    def set_printig_time(self, time):
        self.printing_time = time

    def set_data_keys(self, data_keys):
        self.data_keys = data_keys

    def set_all_data(self, all_data):
        self.all_data = all_data

    def set_data(self, data):
        self.data = data

    def set_finished_read(self):
        self.gcode_parser_thread.quit()
        self.is_loaded = True
        self.done_loading_callback()
        #self.controller.set_gcode()

    def set_finished_copy(self):
        self.gcode_copy_thread.quit()
        #print(str(self.writing_done_callback))
        self.writing_done_callback()

    def set_color_change_data(self, data):
        self.color_change_data = data


    def write_with_changes_in_thread(self, filename_in, filename_out, update_function):
        self.gcode_copy.filename_in = filename_in
        self.gcode_copy.filename_out = filename_out
        self.gcode_copy.color_change_lst = self.color_change_data
        self.gcode_copy.moveToThread(self.gcode_copy_thread)

        self.gcode_copy_thread.started.connect(self.gcode_copy.write_file)

        self.gcode_copy.finished.connect(self.set_finished_copy)
        self.gcode_copy.set_update_progress.connect(update_function)

        self.gcode_copy_thread.start()



class GcodeCopyRunner(QObject):
    finished = pyqtSignal()
    set_update_progress = pyqtSignal(int)

    def __init__(self, filename_in, filename_out, color_change_lst):
        super(GcodeCopyRunner, self).__init__()
        self.filename_in = filename_in
        self.filename_out = filename_out
        self.color_change_lst = color_change_lst
        self.is_running = True


    def write_file(self):

        if self.color_change_lst:
            self.copy_file_with_progress_and_color_changes(self.filename_in, self.filename_out)
        else:
            self.copy_file_with_progress(self.filename_in, self.filename_out)

    def copy_file_with_progress_and_color_changes(self, filename_in, filename_out, length=16*1024):
        f_src = open(filename_in, 'r')
        f_dst = open(filename_out, 'w')

        fsrc_size = os.fstat(f_src.fileno()).st_size

        copied = 0
        line_number = 0
        while self.is_running is True:
            buf = f_src.readline()
            line_number += 1
            if not buf:
                self.finished.emit()
                break
            if line_number in self.color_change_lst:
                f_dst.write("M600\n")
            f_dst.write(buf)
            copied += len(buf)
            self.set_update_progress.emit((copied * 1. / fsrc_size * 1.)*100)

            #progress_callback((copied * 1. / fsrc_size * 1.))


    def copy_file_with_progress(self, filename_in, filename_out, length=16*1024):
        f_src = open(filename_in, 'r')
        f_dst = open(filename_out, 'w')

        fsrc_size = os.fstat(f_src.fileno()).st_size

        copied = 0
        while self.is_running is True:
            buf = f_src.read(length)
            if not buf:
                self.finished.emit()
                break
            f_dst.write(buf)
            copied += len(buf)
            self.set_update_progress.emit((copied * 1. / fsrc_size * 1.)*100)
            #progress_callback((copied * 1. / fsrc_size * 1.))



class GcodeParserRunner(QObject):
    finished = pyqtSignal()
    set_data_keys = pyqtSignal(list)
    set_data = pyqtSignal(dict)
    set_all_data = pyqtSignal(list)
    set_printing_time = pyqtSignal(float)
    set_update_progress = pyqtSignal(int)


    def __init__(self, controller, filename):
        super(GcodeParserRunner, self).__init__()
        self.is_running = True
        self.controller = controller
        self.filename = filename

        self.data = defaultdict(list)
        self.all_data = []
        self.data_keys = set()
        self.actual_z = '0.0'
        self.speed = 0.0
        self.extrusion = 0.0
        self.z_hop = False
        self.last_point = np.array([0.0, 0.0, 0.0])
        self.actual_point = np.array([0.0, 0.0, 0.0])

        self.printing_time = 0.0
        self.filament_length = 0.0

    def load_gcode_file_with_profile(self):
        cProfile.runctx('self.load_gcode_file()', globals(), locals(), 'gcode_parser.profile')

    #@timing
    def load_gcode_file(self):
        file = QFile(self.filename)
        file.open(QIODevice.ReadOnly | QIODevice.Text)
        in_stream = QTextStream(file)
        file_size = np.array([file.size()])
        counter_size = int(file_size/800.)
        #print(counter_size)
        counter = 0
        line = 0
        line_number = 0

        while in_stream.atEnd() is False and self.is_running is True:
        #for line in in_stream.readAll():
            if self.is_running is False:
                break

            counter+=1
            if self.set_update_progress and counter==counter_size:
                #in_stream.pos() je hodne pomala funkce takze na ni pozor!!!
                progress = (in_stream.pos()*1./file_size) * 100.
                self.set_update_progress.emit(int(progress))
                counter=0

            line = in_stream.readLine()

            #print(line)
            # self.process_line(line)
            bits = line.split(';', 1)
            if bits[0] == '':
                line_number+=1
                continue
            if 'G1 ' in bits[0]:
                self.parse_g1_line(bits, line_number)
            else:
                line_number += 1

        if self.is_running == False:
            self.set_update_progress.emit(0)

        self.printing_time = self.calculate_time_of_print()
        #self.printing_time = 0.
        self.filament_length = 0.0  # self.calculate_length_of_filament()

        ###
        self.non_extruding_layers = []
        for i in self.data:
            layer_flag = 'M'
            for l in self.data[i]:
                _start, _end, flag, _speed, _extr, _line = l
                if flag in ['E', 'E-sk', 'E-su', 'E-i', 'E-p']:
                    layer_flag = 'E'
                    break
            if layer_flag == 'M':
                self.non_extruding_layers.append(i)

        for i in self.non_extruding_layers:
            self.data.pop(i, None)

        self.data_keys = set()
        self.data_keys = set(self.data)
        self.data_keys = sorted(self.data_keys, key=float)
        #self.data_keys.sort(key=lambda x: float(x))


        self.set_data_keys.emit(self.data_keys)
        self.set_data.emit(self.data)
        self.set_all_data.emit(self.all_data)
        self.set_printing_time.emit(self.printing_time)

        self.finished.emit()

    #@timing
    def calculate_time_of_print(self):
        time_of_print = 0.0
        all_data = self.all_data

        #vectorization speed up
        a_vect = np.array([i[0] for i in all_data])
        b_vect = np.array([i[1] for i in all_data])
        speed_vect = np.array([i[3] for i in all_data])

        vect_vect = b_vect - a_vect
        leng_vect = np.linalg.norm(vect_vect, axis=1)
        time_vect = np.divide(leng_vect, speed_vect)
        time_of_print = np.sum(time_vect)

        #Magic constant :-)
        time_of_print *=1.1

        return time_of_print*60

    def calculate_length_of_filament(self):
        length = 0.0
        for line in self.all_data:
            if line[2]=='M':
                continue
            a = np.array(line[0])
            b = np.array(line[1])
            vect = b-a
            leng = np.linalg.norm(vect)
            length+=leng

        return length

    def set_print_info_text(self, string):
        print("Info: " + string)

    #only G1 lines
    def parse_g1_line(self, data, line_number):
        if len(data)>1:
            text = data[0]
            comment = data[1]
        else:
            text = data[0]
            comment = ""

        line = text.split(' ')
        line = list(filter(None, line))
        #print(line)

        #print(comment)
        comment_line = comment.split(' ')
        comment_line = list(filter(None, comment_line))
        if len(comment_line)==0:
            if 'Z' in line[1]:
                # Set of Z axis
                new_z = float(line[1][1:])
                self.actual_z = "%.2f" % new_z
                self.last_point[2] = new_z
                return
            elif 'F' in line[1]:
                self.speed = float(line[1][1:])
            elif len(line) < 4:
                return
            elif 'X' in line[1] and 'Y' in line[2] and not ('E' in line[3]) and 'F' in line[3]:
                # elif 'X' in line[1] and 'Y' in line[2] and not ('E' in line[3]) and 'F' in line[3]:
                # Move point
                self.actual_point = np.array([np.float(line[1][1:]), np.float(line[2][1:]), np.float(self.actual_z)])
                if self.last_point.any():
                    self.add_line(self.last_point, self.actual_point, self.actual_z, 'M', np.float(line[3][1:]), line_number=line_number)
                    self.last_point = np.array(self.actual_point)
                else:
                    self.last_point = np.array(self.actual_point)
            elif 'X' in line[1] and 'Y' in line[2] and 'E' in line[3]:
                # elif 'X' in line[1] and 'Y' in line[2] and 'E' in line[3]:
                # Extrusion point
                self.actual_point = np.array([np.float(line[1][1:]), np.float(line[2][1:]), np.float(self.actual_z)])
                self.extrusion = np.float(line[3][1:])
                if self.last_point.any():
                    if np.float(line[3][1:]) > 0.:
                        if len(comment_line) > 0:
                            if 'infill' in comment_line[0]:
                                type = 'E-i'
                            elif 'perimeter' in comment_line[0]:
                                type = 'E-p'
                            elif 'support' in comment_line[0] and 'material' in comment_line[1]:
                                type = 'E-su'
                            elif 'skirt' in comment_line[0]:
                                type = 'E-sk'
                            else:
                                type = 'E'
                        else:
                            type = 'E'
                    else:
                        type = 'M'

                    self.add_line(self.last_point, self.actual_point, self.actual_z, type, self.speed, self.extrusion, line_number=line_number)
                    self.last_point = np.array(self.actual_point)
                else:
                    self.last_point = np.array(self.actual_point)
            elif 'X' in line[1] and 'E' in line[2] and 'F' in line[3]:
                # elif 'X' in line[1] and 'E' in line[2] and 'F' in line[3]:
                # Extrusion point
                self.actual_point[0] = np.float(line[1][1:])
                self.extrusion = np.float(line[2][1:])
                if self.last_point.any():
                    if np.float(line[2][1:]) > 0.:
                        if len(comment_line) > 0:
                            if 'infill' in comment_line[0]:
                                type = 'E-i'
                            elif 'perimeter' in comment_line[0]:
                                type = 'E-p'
                            elif 'support' in comment_line[0] and 'material' in comment_line[1]:
                                type = 'E-su'
                            elif 'skirt' in comment_line[0]:
                                type = 'E-sk'
                            else:
                                type = 'E'
                        else:
                            type = 'E'
                    else:
                        type = 'M'
                    self.add_line(self.last_point, self.actual_point, self.actual_z, type, np.float(line[3][1:]), self.extrusion, line_number=line_number)
                    self.last_point = np.array(self.actual_point)
                else:
                    self.last_point = np.array(self.actual_point)
            elif 'Y' in line[1] and 'F' in line[2]:
                # elif 'Y' in line[1] and 'F' in line[2]:
                # Move point
                self.actual_point[1] = np.float(line[1][1:])

                if self.last_point:
                    self.add_line(self.last_point, self.actual_point, self.actual_z, 'M', np.float(line[2][1:]), line_number=line_number)
                    self.last_point = np.array(self.actual_point)
                else:
                    self.last_point = np.array(self.actual_point)
        else:
            if 'Z' in line[1]:
                # Set of Z axis
                new_z = np.float(line[1][1:])
                self.actual_z = "%.2f" % new_z
                self.last_point[2] = new_z
                return
            elif 'F' in line[1]:
                self.speed = np.float(line[1][1:])
            elif len(line) < 4:
                return
            elif 'X' in line[1] and 'Y' in line[2] and not ('E' in line[3]) and 'F' in line[3] and not (
                    'intro' in comment_line[0] and 'line' in comment_line[1]):
                # elif 'X' in line[1] and 'Y' in line[2] and not ('E' in line[3]) and 'F' in line[3]:
                # Move point
                self.actual_point = np.array([np.float(line[1][1:]), np.float(line[2][1:]), np.float(self.actual_z)])
                if self.last_point.any():
                    self.add_line(self.last_point, self.actual_point, self.actual_z, 'M', np.float(line[3][1:]), line_number=line_number)
                    self.last_point = np.array(self.actual_point)
                else:
                    self.last_point = np.array(self.actual_point)
            elif 'X' in line[1] and 'Y' in line[2] and 'E' in line[3] and not (
                    'intro' in comment_line[0] and 'line' in comment_line[1]):
                # elif 'X' in line[1] and 'Y' in line[2] and 'E' in line[3]:
                # Extrusion point
                self.actual_point = np.array([np.float(line[1][1:]), np.float(line[2][1:]), np.float(self.actual_z)])
                self.extrusion = np.float(line[3][1:])
                if self.last_point.any():
                    if np.float(line[3][1:]) > 0.:
                        if len(comment_line) > 0:
                            if 'infill' in comment_line[0]:
                                type = 'E-i'
                            elif 'perimeter' in comment_line[0]:
                                type = 'E-p'
                            elif 'support' in comment_line[0] and 'material' in comment_line[1]:
                                type = 'E-su'
                            elif 'skirt' in comment_line[0]:
                                type = 'E-sk'
                            else:
                                type = 'E'
                        else:
                            type = 'E'
                    else:
                        type = 'M'

                    self.add_line(self.last_point, self.actual_point, self.actual_z, type, self.speed, self.extrusion, line_number=line_number)
                    self.last_point = np.array(self.actual_point)
                else:
                    self.last_point = np.array(self.actual_point)
            elif 'X' in line[1] and 'E' in line[2] and 'F' in line[3] and not (
                    'intro' in comment_line[0] and 'line' in comment_line[1]):
                # elif 'X' in line[1] and 'E' in line[2] and 'F' in line[3]:
                # Extrusion point
                self.actual_point[0] = np.float(line[1][1:])
                self.extrusion = np.float(line[2][1:])
                if self.last_point.any():
                    if np.float(line[2][1:]) > 0.:
                        if len(comment_line) > 0:
                            if 'infill' in comment_line[0]:
                                type = 'E-i'
                            elif 'perimeter' in comment_line[0]:
                                type = 'E-p'
                            elif 'support' in comment_line[0] and 'material' in comment_line[1]:
                                type = 'E-su'
                            elif 'skirt' in comment_line[0]:
                                type = 'E-sk'
                            else:
                                type = 'E'
                        else:
                            type = 'E'
                    else:
                        type = 'M'
                    self.add_line(self.last_point, self.actual_point, self.actual_z, type, np.float(line[3][1:]), self.extrusion, line_number=line_number)
                    self.last_point = np.array(self.actual_point)
                else:
                    self.last_point = np.array(self.actual_point)
            elif 'Y' in line[1] and 'F' in line[2] and not ('go' in comment_line[0] and 'outside' in comment_line[1]):
                # elif 'Y' in line[1] and 'F' in line[2]:
                # Move point
                self.actual_point[1] = np.float(line[1][1:])

                if self.last_point.any():
                    self.add_line(self.last_point, self.actual_point, self.actual_z, 'M', np.float(line[2][1:]), line_number=line_number)
                    self.last_point = np.array(self.actual_point)
                else:
                    self.last_point = np.array(self.actual_point)

        return

    def add_line(self, first_point, second_point, actual_z, type, speed=0., extrusion=0., line_number = -1):
        key = actual_z
        if key in self.data_keys:
            self.data[key].append([first_point, second_point, type, speed, extrusion, line_number])
            self.all_data.append([first_point, second_point, type, speed, extrusion, line_number])
        else:
            self.data_keys.add(key)
            self.data[key] = []
            self.data[key].append([first_point, second_point, type, speed, extrusion, line_number])
            self.all_data.append([first_point, second_point, type, speed, extrusion, line_number])




    '''
    def add_point(self, x, y, z, actual_z):
        key = actual_z
        if key in self.data_keys:
            self.data[key].append([x, y, z])
            self.all_data.append([x, y, z])
        else:
            self.data_keys.add(key)
            self.data[key] = []
            self.data[key].append([x, y, z])
            self.all_data.append([x, y, z])
    '''