import time
from fastnumbers import fast_float

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
                '0.0':[[1.0, 2.0],[2.0, 1.2],[3.0,11.0]],
                '0.15':[[0.0,0.0], [...], ...],
                ''
            }
        """

        self.data = {}
        self.data_keys = []
        self.actual_z = '0.0'



        #buffering=(2 << 16) + 8
        with open(filename, 'r', buffering=(2 << 16) + 8) as f:
            for line in f:
                #striped_line = line.rstrip()
                #bits = striped_line.split(';', 1)
                bits = line.split(';', 1)
                if bits[0] == '':
                    continue
                if 'G1' in bits[0]:
                    self.parse_line(bits[0])
                else:
                    continue

    def parse_line(self, text):
        line = text.split(' ')
        if 'Z' in line[1]:
            self.actual_z = line[1][1:]
            return
        elif 'X' in line[1] and 'Y' in line[2] and 'E' in line[3]:
            data_x = fast_float(line[1][1:])
            data_y = fast_float(line[2][1:])
            self.add_point(data_x, data_y, self.actual_z)
        return


    def add_point(self, x, y, z):
        key = z
        if key in self.data_keys:
            self.data[key].append([x,y])
        else:
            self.data_keys.append(key)
            self.data[key] = []
            self.data[key].append([x, y])


