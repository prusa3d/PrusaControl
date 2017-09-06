# -*- coding: utf-8 -*-
__author__ = 'Tibor Vavra'

import time
#from fastnumbers import fast_float
from collections import defaultdict
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


DEBUG = False

class GCode(object):

    def __init__(self, filename, controller, done_loading_callback, done_writing_callback):
        self.controller = controller
        self.done_loading_callback = done_loading_callback
        self.writing_done_callback = done_writing_callback
        self.data = defaultdict(list)
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
        print("Cancel presset")
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
        print("Cancel writing gcode")
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
        print("reading in thread")
        self.gcode_parser.moveToThread(self.gcode_parser_thread)
        self.done_loading_callback = after_done_function

        # connect all signals to thread class
        self.gcode_parser_thread.started.connect(self.gcode_parser.load_gcode_file)
        # connect all signals to parser class
        self.gcode_parser.finished.connect(self.set_finished_read)
        self.gcode_parser.update_progressbar=True
        self.gcode_parser.set_update_progress.connect(update_progressbar_function)
        self.gcode_parser.set_data_keys.connect(self.set_data_keys)
        self.gcode_parser.set_data.connect(self.set_data)
        self.gcode_parser.set_all_data.connect(self.set_all_data)
        self.gcode_parser.set_printing_time.connect(self.set_printig_time)

        self.gcode_parser_thread.start()


    def read_in_realtime(self):
        print("Read in realtime")
        self.gcode_parser.set_data_keys.connect(self.set_data_keys)
        self.gcode_parser.set_data.connect(self.set_data)
        self.gcode_parser.set_all_data.connect(self.set_all_data)
        self.gcode_parser.set_printing_time.connect(self.set_printig_time)
        self.gcode_parser.update_progressbar=False

        print("start read procedure")
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
        self.update_progressbar=False

        self.data = defaultdict(list)
        self.all_data = []
        self.sleep_data = []
        self.tool_change_data = []
        self.data_keys = set()
        self.actual_z = '0.0'
        self.speed = 0.0
        self.extrusion = 0.0
        self.z_hop = False
        self.last_point = np.array([0.0, 0.0, 0.0])
        self.actual_point = np.array([0.0, 0.0, 0.0])
        self.absolute_coordinates = True

        self.printing_time = 0.0
        self.filament_length = 0.0



    def load_gcode_file(self):
        file = QFile(self.filename)
        file.open(QIODevice.ReadOnly | QIODevice.Text)
        in_stream = QTextStream(file)
        file_size = file.size()
        counter = 0
        line = 0
        line_number = 0
        while not in_stream.atEnd() and self.is_running is True:

            if self.update_progressbar:
                if counter==10000:
                    #in_stream.pos() je hodne pomala funkce takze na ni pozor!!!
                    progress = (in_stream.pos()*1./file_size*1.) * 100.
                    self.set_update_progress.emit(int(progress))
                    counter=0
                else:
                    counter+=1

            line = in_stream.readLine()
            bits = line.split(';', 1)
            bits_len = len(bits)

            if bits[0] == '':
                line_number+=1
                if bits_len > 1:
                    if bits[0] == '' and bits[1] == "END gcode for filament":
                        break
                continue

            if 'G1 ' in bits[0]:
                self.parse_g1_line_new(bits, line_number)
            elif 'G4' in bits[0]:
                self.parse_g4_line(bits, line_number)
            elif 'T0' in bits[0] or 'T1' in bits[0] or 'T2' in bits[0] or 'T3' in bits[0]:
                self.parse_t_line(bits, line_number)
            elif 'G90' in bits[0]:
                self.absolute_coordinates = True
            elif 'G91' in bits[0]:
                self.absolute_coordinates = False
            else:
                if DEBUG:
                    print("Nezpracovano: " + str(bits))
                line_number += 1
                continue
            line_number += 1

        if self.is_running is False and self.update_progressbar is True:
            self.set_update_progress.emit(0)

        self.printing_time = self.calculate_time_of_print()
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


        self.set_data_keys.emit(self.data_keys)
        self.set_data.emit(self.data)
        self.set_all_data.emit(self.all_data)
        self.set_printing_time.emit(self.printing_time)

        self.finished.emit()


    def calculate_time_of_print(self):
        time_of_print = 0.0
        all_data = self.all_data
        number_of_tool_change = len(self.tool_change_data)

        #vectorization speed up
        a_vect = np.array([i[0] for i in all_data])
        b_vect = np.array([i[1] for i in all_data])
        speed_vect = np.array([i[3] for i in all_data])

        vect_vect = b_vect - a_vect
        leng_vect = np.linalg.norm(vect_vect, axis=1)
        time_vect = np.divide(leng_vect, speed_vect)
        time_of_print = np.sum(time_vect)

        #Magic constant :-)
        time_of_print *= 1.1

        sum_of_sleep = np.sum(self.sleep_data)
        print("Sum of sleep: " + str(sum_of_sleep))
        time_of_print += sum_of_sleep

        print("Time of print: " +str(time_of_print))

        #speed is in mm/min => mm/sec
        return time_of_print*60.

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

    #only T lines
    def parse_t_line(self, data, line_number):
        if len(data)>1:
            text = data[0]
            comment = data[1]
        else:
            text = data[0]
            comment = ""

        line = text.split(' ')
        line = list(filter(None, line))
        line_len = len(line)

        comment_line = comment.split(' ')
        comment_line = list(filter(None, comment_line))

        if 'T?' in line[0]:
            return
        else:
            self.tool_change_data.append(int(line[0][1:]))


    #only G4 lines
    def parse_g4_line(self, data, line_number):
        if len(data)>1:
            text = data[0]
            comment = data[1]
        else:
            text = data[0]
            comment = ""

        line = text.split(' ')
        line = list(filter(None, line))
        line_len = len(line)

        comment_line = comment.split(' ')
        comment_line = list(filter(None, comment_line))

        if line_len > 1:
            if 'S' in line[1]:
                self.sleep_data.append(float(line[1][1:]))
                #set sleep




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

        #print(comment)
        comment_line = comment.split(' ')
        comment_line = list(filter(None, comment_line))

        if len(comment_line)==0:
            # Uncomented gcode
            if 'Z' in line[1]:
                # Set of Z axis
                new_z = float(line[1][1:])
                self.actual_z = "%.2f" % new_z
                self.last_point[2] = new_z
                return
            elif 'F' in line[1]:
                self.speed = float(line[1][1:])
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

            elif 'Y' in line[1] and 'E' in line[2]:
                # G1 Y199.750 E0.3154 F2400
                # G1 Y199.750 E0.3154
                speed = 0.

                if len(line) > 3:
                    if 'F' in line[3]:
                        speed = np.float(line[3][1:])

                self.actual_point[1] = np.float(line[1][1:])
                self.extrusion = np.float(line[2][1:])

                self.add_line(self.last_point, self.actual_point, self.actual_z, 'E', speed, self.extrusion, line_number=line_number)
                self.last_point = np.array(self.actual_point)

            elif 'X' in line[1]:
                print("Zpracovavam: " + str(line))
                # G1 X179.750 F7000
                # G1 X240.250 E1.9299
                speed = 0.

                if len(line) > 2:
                    if 'F' in line[2]:
                        speed = np.float(line[2][1:])
                    elif 'E' in line[2]:
                        self.extrusion = np.float(line[2][1:])

                self.actual_point[0] = np.float(line[1][1:])

                self.add_line(self.last_point, self.actual_point, self.actual_z, 'E', speed, self.extrusion, line_number=line_number)
                self.last_point = np.array(self.actual_point)

            elif DEBUG:
                print("Nezpracovano: " + str(line) + ' ' + str(comment_line))

        else:
            #Comented gcode
            if 'Z' in line[1]:
                # G1 Z0.350 F7200.000 ; move to next layer (1)
                # Set of Z axis
                new_z = np.float(line[1][1:])
                self.actual_z = "%.2f" % new_z
                self.last_point[2] = new_z
                return
            elif 'F' in line[1]:
                # G1 F5760
                self.speed = np.float(line[1][1:])

            elif 'X' in line[1] and 'Y' in line[2] and not ('E' in line[3]) and 'F' in line[3] and not (
                    'intro' in comment_line[0] and 'line' in comment_line[1]):
                # elif 'X' in line[1] and 'Y' in line[2] and not ('E' in line[3]) and 'F' in line[3]:
                # Move point
                #
                self.actual_point = np.array([np.float(line[1][1:]), np.float(line[2][1:]), np.float(self.actual_z)])
                if self.last_point.any():
                    self.add_line(self.last_point, self.actual_point, self.actual_z, 'M', np.float(line[3][1:]), line_number=line_number)
                    self.last_point = np.array(self.actual_point)
                else:
                    self.last_point = np.array(self.actual_point)
            elif 'X' in line[1] and 'Y' in line[2] and 'E' in line[3] and not (
                    'intro' in comment_line[0] and 'line' in comment_line[1]):
                # G1 X122.438 Y106.154 E0.01540 ; infill
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

            elif 'Y' in line[1] and 'E' in line[2]:
                # G1 Y199.750 E0.3154 F2400
                # G1 Y199.750 E0.3154
                speed = 0.

                if len(line) > 3:
                    if 'F' in line[3]:
                        speed = np.float(line[3][1:])

                self.actual_point[1] = np.float(line[1][1:])
                self.extrusion = np.float(line[2][1:])

                self.add_line(self.last_point, self.actual_point, self.actual_z, 'E', speed, self.extrusion, line_number=line_number)
                self.last_point = np.array(self.actual_point)

            elif 'X' in line[1]:
                #print("Zpracovavam: " + str(line))
                # G1 X179.750 F7000
                # G1 X240.250 E1.9299
                speed = 0.

                if len(line) > 2:
                    if 'F' in line[2]:
                        speed = np.float(line[2][1:])
                    elif 'E' in line[2]:
                        self.extrusion = np.float(line[2][1:])

                self.actual_point[0] = np.float(line[1][1:])

                self.add_line(self.last_point, self.actual_point, self.actual_z, 'E', speed, self.extrusion,
                              line_number=line_number)
                self.last_point = np.array(self.actual_point)

            elif DEBUG:
                print("Nezpracovano: " + str(line) +' ' +str(comment_line))

        return

    def parse_g1_line_new(self, data, line_number):
        # get raw line data and line_number to know position in file
        # data is list from line from file devided by ;
        # [0] data and [1] is comment

        if len(data)>1:
            text = data[0]
            comment = data[1]
        else:
            text = data[0]
            comment = ""

        line = text.split(' ')
        line = list(filter(None, line))
        line_len = len(line)

        #print(comment)
        comment_line = comment.split(' ')
        comment_line = list(filter(None, comment_line))
        comment_line_len = len(comment_line)

        if 'Z' in line[1]:
            # Set of Z axis
            # G1 Z1.850 F7200.000 ; lift Z
            new_z = float(line[1][1:])
            if self.absolute_coordinates:
                self.actual_z = "%.2f" % new_z
                self.last_point = np.array([self.last_point[0], self.last_point[1], new_z])
            else:
                self.actual_z = "%.2f" % (self.last_point[2] + new_z)
                self.last_point = np.array([self.last_point[0], self.last_point[1], self.last_point[2] + new_z])
            return
        elif 'F' in line[1]:
            # Set of feed rate(speed mm/m)
            # G1 F5760
            self.speed = np.float(line[1][1:])
        elif 'X' in line[1]:
            # Set move point(possible extrusion)
            # G1 X119.784 Y109.613 E0.00507 ; perimeter
            # G1 X119.731 Y110.014 F7200.000 ; move to first perimeter point
            # G1 X118.109 Y101.483 E0.03127 ; infill
            # G1 X121.899 Y107.591 E-0.97707 ; wipe and retract
            # G1 X179.750 F7000
            # G1 X240.250 E1.9299


            if line_len == 4:

                if 'E' in line[2] and 'F' in line[3]:
                    # G1 X181.500 E0.0217 F2900
                    self.extrusion = np.float(line[2][1:])
                    self.speed = np.float(line[3][1:])
                    self.actual_point = np.array([np.float(line[1][1:]), self.actual_point[1], np.float(self.actual_z)])
                elif 'E' in line[3]:
                    # G1 X119.784 Y109.613 E0.00507 ; perimeter
                    # G1 X118.109 Y101.483 E0.03127 ; infill
                    # G1 X121.899 Y107.591 E-0.97707 ; wipe and retract
                    self.extrusion = np.float(line[3][1:])
                    self.actual_point = np.array(
                        [np.float(line[1][1:]), np.float(line[2][1:]), np.float(self.actual_z)])
                elif 'F' in line[3]:
                    # G1 X119.731 Y110.014 F7200.000 ; move to first perimeter point
                    self.speed = np.float(line[3][1:])
                    self.actual_point = np.array([np.float(line[1][1:]), np.float(line[2][1:]), np.float(self.actual_z)])

            elif line_len == 3:
                # G1 X179.750 F7000
                # G1 X240.250 E1.9299

                if 'E' in line[2]:
                    self.extrusion = np.float(line[2][1:])
                elif 'F' in line[2]:
                    self.speed = np.float(line[2][1:])

                self.actual_point = np.array([np.float(line[1][1:]), self.actual_point[1], self.actual_point[2]])


            if self.extrusion > 0.:
                if comment_line_len > 0:
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

            if self.last_point.any():
                self.add_line(self.last_point, self.actual_point, self.actual_z, type, self.speed, self.extrusion,
                              line_number=line_number)
                self.last_point = np.array(self.actual_point)
            else:
                self.last_point = np.array(self.actual_point)


        elif 'Y' in line[1]:
            # Set move point(possible extrusion)
            # G1 Y199.750 E0.3154 F2400
            # G1 Y185.250 E0.3154

            if line_len == 4:
                if 'F' in line[3]:
                    # G1 Y199.750 E0.3154 F2400
                    self.speed = np.float(line[3][1:])

            self.extrusion = np.float(line[2][1:])

            self.actual_point = np.array([self.actual_point[0], np.float(line[1][1:]), self.actual_point[2]])

            if self.extrusion > 0.:
                type = 'E'
            else:
                type = 'M'

            if self.last_point.any():
                self.add_line(self.last_point, self.actual_point, self.actual_z, type, self.speed, self.extrusion,
                              line_number=line_number)
                self.last_point = np.array(self.actual_point)
            else:
                self.last_point = np.array(self.actual_point)

        elif 'E' in line[1] and 'F' in line[2]:
            # G1 E-15.0000 F5000

            self.extrusion = np.float(line[1][1:])
            self.speed = np.float(line[2][1:])


        else:
            if DEBUG:
                print("Nezpracovano: " + str(line) + ' ' + str(comment_line))

        return



    def add_line(self, first_point, second_point, actual_z, type, speed=0., extrusion=0., line_number = -1):
        #print("Add line: " + str(first_point) + ' ' + str(second_point) + ' type: ' + str(type) + ' ' + str(line_number))

        key = deepcopy(actual_z)
        if key in self.data_keys:
            self.data[key].append([deepcopy(first_point),
                                   deepcopy(second_point),
                                   deepcopy(type),
                                   deepcopy(speed),
                                   deepcopy(extrusion),
                                   deepcopy(line_number)])
            self.all_data.append([deepcopy(first_point),
                                  deepcopy(second_point),
                                  deepcopy(type),
                                  deepcopy(speed),
                                  deepcopy(extrusion),
                                  deepcopy(line_number)])
        else:
            self.data_keys.add(key)
            self.data[key] = []
            self.data[key].append([deepcopy(first_point),
                                   deepcopy(second_point),
                                   deepcopy(type),
                                   deepcopy(speed),
                                   deepcopy(extrusion),
                                   deepcopy(line_number)])
            self.all_data.append([deepcopy(first_point),
                                  deepcopy(second_point),
                                  deepcopy(type),
                                  deepcopy(speed),
                                  deepcopy(extrusion),
                                  deepcopy(line_number)])




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