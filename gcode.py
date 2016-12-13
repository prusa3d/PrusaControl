import time
#from fastnumbers import fast_float
from copy import deepcopy
from pprint import pprint

import numpy as np


def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print('%s function took %0.3f ms' % (f.func_name, (time2-time1)*1000.0))
        return ret
    return wrap

class GCode(object):
    #@timing
    def __init__(self, filename):
        """
            data =
            {
                '0.0':[[[1.0, 2.0, 0.0],[2.0, 1.2, 0.0], 'E']], [[2.0, 1.2, 0.0], [3.0,11.0, 0.0], 'M'],
                '0.15':[[[0.0,0.0, 0.15], [...]], [...], ...],
                ''
            }
        """

        self.data = {}
        self.all_data = []
        self.data_keys = []
        self.actual_z = '0.0'
        self.speed = 0.0
        self.last_point = [0.0, 0.0, 0.0]
        self.actual_point = [0.0, 0.0, 0.0]

        self.printing_time = 0.0
        self.filament_length = 0.0



        #buffering=(2 << 16) + 8
        with open(filename, 'r', buffering=(2 << 16) + 8) as f:
            for line in f:
                #striped_line = line.rstrip()
                #bits = striped_line.split(';', 1)
                bits = line.split(';', 1)
                if bits[0] == '':
                    continue
                if 'G1' in bits[0]:
                    self.parse_g1_line(bits[0])
                else:
                    continue

        self.data_keys.sort(key=lambda x: float(x))

        self.printing_time = self.calculate_time_of_print()
        self.filament_length = 0.0#self.calculate_length_of_filament()


    def calculate_time_of_print(self):
        time_of_print = 0.0
        for line in self.all_data:
            a = np.array(line[0])
            b = np.array(line[1])
            speed = line[3] #mm/min
            vect = b-a
            leng = np.linalg.norm(vect)
            time = leng / speed
            time_of_print += time

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
    def parse_g1_line(self, text):
        line = text.split(' ')
        line = filter(None, line)
        if 'Z' in line[1]:
            #Set of Z axis
            self.actual_z = "%.2f" % float(line[1][1:])

            self.last_point =[]
            return

        if 'F' in line[1]:
            self.speed = float(line[1][1:])
        elif len(line)<4:
            return
        elif 'X' in line[1] and 'Y' in line[2] and not('E' in line[3]) and 'F' in line[3]:
            #Move point
            self.actual_point = [float(line[1][1:]), float(line[2][1:]), float(self.actual_z)]
            if self.last_point:
                self.add_line(self.last_point, self.actual_point, self.actual_z, 'M', float(line[3][1:]))
                self.last_point = deepcopy(self.actual_point)
            else:
                self.last_point = deepcopy(self.actual_point)
        elif 'X' in line[1] and 'Y' in line[2] and 'E' in line[3]:
            #Extrusion point
            self.actual_point = [float(line[1][1:]), float(line[2][1:]), float(self.actual_z)]
            if self.last_point:
                if float(line[3][1:])>0.:
                    type = 'E'
                else:
                    type = 'M'
                self.add_line(self.last_point, self.actual_point, self.actual_z, type, self.speed)
                self.last_point = deepcopy(self.actual_point)
            else:
                self.last_point = deepcopy(self.actual_point)
        elif 'X' in line[1] and 'E' in line[2] and 'F' in line[3]:
            print("nasel samostatne X")
            #Extrusion point
            self.actual_point[0] = float(line[1][1:])

            if self.last_point:
                if float(line[2][1:])>0.:
                    type = 'E'
                else:
                    type = 'M'
                self.add_line(self.last_point, self.actual_point, self.actual_z, type, float(line[3][1:]))
                self.last_point = deepcopy(self.actual_point)
            else:
                self.last_point = deepcopy(self.actual_point)
        elif 'Y' in line[1] and 'F' in line[2]:
            print("nasel samostatne Y")
            #Move point
            self.actual_point[1] = float(line[1][1:])

            if self.last_point:
                self.add_line(self.last_point, self.actual_point, self.actual_z, 'M', float(line[2][1:]))
                self.last_point = deepcopy(self.actual_point)
            else:
                self.last_point = deepcopy(self.actual_point)

        return

    def add_line(self, first_point, second_point, actual_z, type, speed=0.):
        key = actual_z
        if key in self.data_keys:
            self.data[key].append([first_point, second_point, type, speed])
            self.all_data.append([first_point, second_point, type, speed])
        else:
            self.data_keys.append(key)
            self.data[key] = []
            self.data[key].append([first_point, second_point, type, speed])
            self.all_data.append([first_point, second_point, type, speed])



    def add_point(self, x, y, z, actual_z):
        key = actual_z
        if key in self.data_keys:
            self.data[key].append([x, y, z])
            self.all_data.append([x, y, z])
        else:
            self.data_keys.append(key)
            self.data[key] = []
            self.data[key].append([x, y, z])
            self.all_data.append([x, y, z])


