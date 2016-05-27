# -*- coding: utf-8 -*-
import numpy
from abc import ABCMeta, abstractmethod
from os.path import basename

from PyQt4.QtCore import QObject
from stl.mesh import Mesh
from random import randint
import math
import itertools
from pprint import pprint

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from copy import deepcopy
from pyrr import matrix44, Vector3, geometric_tests, line, ray, plane, matrix33

glutInit()

class AppScene(object):
    '''
    Class holding data of scene, models, positions, parameters
    it can be used for generating sliced data and rendering data
    '''
    def __init__(self, controller):
        self.controller = controller
        self.model_position_offset = 10.

        self.sceneZero = [.0, .0, .0]
        self.models = []
        self.printable = True

        self.transformation_list = []
        self.actual_list_position = 0

    def save_change(self, instance, change_type, value):
        if not(self.actual_list_position == len(self.transformation_list)):
            #TODO:Vymyslet lepe, toto reseni je nestabilni...
            self.transformation_list = deepcopy(self.transformation_list[:self.actual_list_position])
        self.transformation_list.append([instance, change_type, value])
        self.actual_list_position = len(self.transformation_list)

    def make_undo(self):
        #just move pointer of transformation to -1 or leave on 0
        print(str(self.transformation_list))
        if self.actual_list_position > 1:
            self.actual_list_position -= 1
            instance, change_type, data = self.transformation_list[self.actual_list_position]
            print("Undo: " + change_type +' '+ str(data))
            instance.make_change(False, change_type, data)

    def make_do(self):
        #move pointer of transformation to +1 or leave on last
        print(str(self.transformation_list))
        if self.actual_list_position < len(self.transformation_list):
            self.actual_list_position += 1
            instance, change_type, data = self.transformation_list[self.actual_list_position]
            print("Do: " + change_type +' '+ str(data))
            instance.make_change(True, change_type, data)

    def check_models_name(self):
        for m in self.models:
            number = 0
            for o in self.models:
                if m.filename == o.filename:
                    number+=1
                if number>1:
                    name_list = o.filename.split(".")
                    name_list[0] = "%s%s" % (name_list[0], str(number))
                    o.filename = ".".join(name_list)


    def clearScene(self):
        self.models = []

    def clear_selected_models(self):
        for model in self.models:
            model.selected = False

    def automatic_models_position(self):
        #sort objects over size of bounding sphere
        self.models = sorted(self.models, key=lambda k: k.boundingSphereSize, reverse=True)
        #place biggest object(first one) on center
        #place next object in array on place around center(in clockwise direction) on place zero(center) + 1st object size/2 + 2nd object size/2 + offset
        for i, m in enumerate(self.models):
            self.find_new_position(i, m)

    def find_new_position(self, index, model):
        position_vector = [.0, .0]
        if index == 0:
            self.models[0].pos[0] = position_vector[0]
            self.models[0].pos[1] = position_vector[1]

            self.models[0].max_scene = self.models[0].max + self.models[0].pos
            self.models[0].min_scene = self.models[0].min + self.models[0].pos
            return
        scene_tmp = self.models[:index]
        if index > 0:
            while model.intersection_model_list_model_(scene_tmp):
                for angle in xrange(0, 360, 20):
                    model.pos[0] = math.cos(math.radians(angle)) * (position_vector[0])
                    model.pos[1] = math.sin(math.radians(angle)) * (position_vector[1])

                    model.max_scene = model.max + model.pos
                    model.min_scene = model.min + model.pos

                    #TODO:Add some test for checking if object is inside of printing space of printer
                    if not model.intersection_model_list_model_(scene_tmp):
                        return

                position_vector[0] += model.boundingSphereSize*.1
                position_vector[1] += model.boundingSphereSize*.1


    #TODO:Doplnit setovani hot_bed dimension from settings->controller
    def define_hot_bed(self, param):
        self.hot_bed_dimension = param

    def save_whole_scene_to_one_stl_file(self, filename):
        whole_scene = Mesh(numpy.concatenate([i.get_mesh().data for i in self.models]))
        whole_scene.save(filename)

class Model(object):
    '''
    this is reprezentation of model data
    '''
    newid = itertools.count().next
    def __init__(self):
        #IDs
        self.id = Model.newid()+1

        self.colorId = [(self.id & 0x000000FF) >> 0, (self.id & 0x0000FF00) >> 8, (self.id & 0x00FF0000) >> 16]

        self.rotateXId = self.id * 1001
        self.rotateColorXId = [(self.rotateXId & 0x000000FF) >> 0, (self.rotateXId & 0x0000FF00) >> 8, (self.rotateXId & 0x00FF0000) >> 16]
        self.rotateYId = self.id * 1002
        self.rotateColorYId = [(self.rotateYId & 0x000000FF) >> 0, (self.rotateYId & 0x0000FF00) >> 8, (self.rotateYId & 0x00FF0000) >> 16]
        self.rotateZId = self.id * 1003
        self.rotateColorZId = [(self.rotateZId & 0x000000FF) >> 0, (self.rotateZId & 0x0000FF00) >> 8, (self.rotateZId & 0x00FF0000) >> 16]

        self.scaleXId = self.id * 2005
        self.scaleColorXId = [(self.scaleXId & 0x000000FF) >> 0, (self.scaleXId & 0x0000FF00) >> 8, (self.scaleXId & 0x00FF0000) >> 16]
        self.scaleYId = self.id * 2007
        self.scaleColorYId = [(self.scaleYId & 0x000000FF) >> 0, (self.scaleYId & 0x0000FF00) >> 8, (self.scaleYId & 0x00FF0000) >> 16]
        self.scaleZId = self.id * 2009
        self.scaleColorZId = [(self.scaleZId & 0x000000FF) >> 0, (self.scaleZId & 0x0000FF00) >> 8, (self.scaleZId & 0x00FF0000) >> 16]
        self.scaleXYZId = self.id * 2011
        self.scaleColorXYZId = [(self.scaleXYZId & 0x000000FF) >> 0, (self.scaleXYZId & 0x0000FF00) >> 8, (self.scaleXYZId & 0x00FF0000) >> 16]

        self.parent = None
        #structural data
        self.v0 = []
        self.v1 = []
        self.v2 = []

        self.rotationAxis = []
        self.scaleAxis = []

        self.dataTmp = []

        self.normal = []
        self.displayList = []

        self.mesh = None

        #transformation data, connected to scene
        self.pos = numpy.array([.0, .0, .0])
        self.rot = numpy.array([.0, .0, .0])
        self.scale = numpy.array([1., 1., 1.])
        self.scaleDefault = [.1, .1, .1]
        self.min_scene = [.0, .0, .0]
        self.max_scene = [.0, .0, .0]

        self.matrix = matrix33.create_identity()
        print("Matice identity\n" + ' ' +str(self.matrix))

        #helping data
        self.selected = False
        self.boundingSphereSize = .0
        self.boundingSphereCenter = [.0, .0, .0]
        self.boundingBox = []
        self.boundingMinimalPoint = [.0, .0, .0]
        self.zeroPoint = [.0, .0, .0]
        self.min = [.0, .0, .0]
        self.max = [.0, .0, .0]

        #self.color = [75./255., 119./255., 190./255.]
        self.color = [34./255., 167./255., 240./255.]

        #source file data
        #example car.stl
        self.filename = ""
        self.normalization_flag = False

    def is_in_printing_space(self, printer):
        min = self.min_scene
        max = self.max_scene

        if max[0] <= (printer['printing_space'][0]*.5) and min[0] >= (printer['printing_space'][0]*-.5):
                if max[1] <= (printer['printing_space'][1]*.5) and min[1] >= (printer['printing_space'][1]*-.5):
                    if max[2] <= printer['printing_space'][2] and min[2] >= -0.1:
                        self.parent.controller.set_printable(True)
                        return True
                    else:
                        print("naruseni v Z")
                        self.parent.controller.set_printable(False)
                        return False
                else:
                    print("naruseni v Y")
                    self.parent.controller.set_printable(False)
                    return False
        else:
            print("naruseni v X")
            self.parent.controller.set_printable(False)
            return False

    def get_mesh(self, transform=True):
        print('saving model')
        data = numpy.zeros(len(self.mesh.vectors), dtype=Mesh.dtype)

        mesh = deepcopy(self.mesh)

        mesh.update_min()
        mesh.update_max()

        '''
        mesh.vectors *= numpy.array(self.scale)

        mesh.rotate([1.0, 0.0, 0.0], self.rot[0])
        mesh.rotate([0.0, 1.0, 0.0], self.rot[1])
        mesh.rotate([0.0, 0.0, 1.0], self.rot[2])
        '''

        if transform:
            mesh.vectors += numpy.array(self.pos)

        mesh.vectors /= numpy.array(self.scaleDefault)

        data['vectors'] = mesh.vectors

        mesh.update_min()
        mesh.update_max()

        return Mesh(data)

    def __str__(self):
        return "Mesh: " + str(self.id) + ' ' + str(self.color)

    def closest_point(self, a, b, p):
        ab = Vector([b.x-a.x, b.y-a.y, b.z-a.z])
        abSquare = numpy.dot(ab.getRaw(), ab.getRaw())
        ap = Vector([p.x-a.x, p.y-a.y, p.z-a.z])
        apDotAB = numpy.dot(ap.getRaw(), ab.getRaw())
        t = apDotAB / abSquare
        q = Vector([a.x+ab.x*t, a.y+ab.y*t, a.z+ab.z*t])
        return q

    def intersection_ray_bounding_sphere(self, start, end):
        v = Vector3(self.boundingSphereCenter)
        matrix = matrix44.from_scale(Vector3(self.scale))
        matrix = matrix * matrix44.from_translation(Vector3(self.pos))

        v = matrix * v

        pt = self.closest_point(Vector(start), Vector(end), Vector(v.tolist()))
        lenght = pt.lenght(v.tolist())
        return lenght < self.boundingSphereSize

    def intersection_model_model(self, model):
        #vector_model_model = Vector(a=model.pos, b=self.pos)
        vector_model_model = self.pos - model.pos
        distance = numpy.linalg.norm(vector_model_model)
        #TODO:Add better alg for detecting intersection(now is only detection of BS)
        if distance >= (model.boundingSphereSize+self.boundingSphereSize):
            return False
        else:
            return True

    def intersection_model_list_model_(self, list):
        for m in list:
            if self.intersection_model_model(m):
                return True
        return False

    def intersection_ray_model(self, rayStart, rayEnd):
        self.dataTmp = itertools.izip(self.v0, self.v1, self.v2)
        matrix = matrix44.from_scale(Vector3(self.scale))
        #TODO:Add rotation
        matrix = matrix * matrix44.from_translation(Vector3(self.pos))

        w = Vector(rayEnd)
        w.minus(rayStart)
        w.normalize()

        for i, tri in enumerate(self.dataTmp):
            v0 = matrix * Vector3(tri[0])
            v1 = matrix * Vector3(tri[1])
            v2 = matrix * Vector3(tri[2])
            v0 = v0.tolist()
            v1 = v1.tolist()
            v2 = v2.tolist()

            b = [.0,.0,.0]
            e1 = Vector(v1)
            e1.minus(v0)
            e2 = Vector(v2)
            e2.minus(v0)

            n = Vector(self.normal[i])

            q = numpy.cross(w.getRaw(), e2.getRaw())
            a = numpy.dot(e1.getRaw(), q)

            if((numpy.dot(n.getRaw(), w.getRaw())>= .0) or (abs(a) <=.0001)):
                continue

            s = Vector(rayStart)
            s.minus(v0)
            s.sqrt(a)

            r = numpy.cross(s.getRaw(), e1.getRaw())
            b[0] = numpy.dot(s.getRaw(), q)
            b[1] = numpy.dot(r, w.getRaw())
            b[2] = 1.0 - b[0] - b[1]

            if ((b[0] < .0) or (b[1] < .0) or (b[2] < .0)):
                continue

            t = numpy.dot(e2.getRaw(), r)
            if (t >= .0):
                return True
            else:
                continue
        return False


    def normalize_object(self):
        r = numpy.array([.0, .0, .0]) - numpy.array(self.boundingSphereCenter)

        self.mesh.vectors = self.mesh.vectors + r

        self.update_min_max()
        self.boundingSphereCenter = numpy.array(self.boundingSphereCenter) + r
        #self.boundingSphereCenter = self.boundingSphereCenter.tolist()

        self.zeroPoint = numpy.array(self.zeroPoint) + r
        self.zeroPoint[2] = self.min[2]

        self.pos = numpy.array([.0, .0, .0]) - self.zeroPoint
        #self.pos = self.pos

        #self.zeroPoint = self.zeroPoint

        self.normalization_flag = True


    def render(self, picking=False, debug=False):
        glPushMatrix()

        glDisable(GL_DEPTH_TEST)
        glBegin(GL_POINTS)
        glColor3f(1,0,0)
        glVertex3f(self.min_scene[0], self.min_scene[1], self.min_scene[2])
        glColor3f(1,0,0)
        glVertex3f(self.max_scene[0], self.max_scene[1], self.max_scene[2])
        glEnd()
        glEnable(GL_DEPTH_TEST)

        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        if picking:
            glColor3ubv(self.colorId)
        else:
            if self.is_in_printing_space(self.parent.controller.actual_printer):
                glColor3fv(self.color)
            else:
                glColor3f(1., .0, .0)

        #glScalef(self.scale[0], self.scale[1], self.scale[2])

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        glNormalPointerf(numpy.tile(self.mesh.normals, 3))
        glVertexPointerf(self.mesh.vectors)

        glDrawArrays(GL_TRIANGLES, 0, len(self.mesh.vectors)*3)

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)

        glPopMatrix()

    def make_display_list(self):
        genList = glGenLists(1)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        glNormalPointerf(numpy.tile(self.mesh.normals, 3))
        glVertexPointerf(self.mesh.vectors)

        glNewList(genList, GL_COMPILE)

        glDrawArrays(GL_TRIANGLES, 0, len(self.mesh.vectors)*3)

        glEndList()

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)

        return genList

    def get_matrix4(self):
        return matrix44.create_from_matrix33(self.matrix)


    def set_move(self, vector):
        vector = numpy.array(vector)
        self.pos += vector
        self.parent.save_change(self, 'move', [vector])
        self.min_scene = self.min + self.pos
        self.max_scene = self.max + self.pos

    def set_rotation(self, vector, alpha):
        if vector.tolist() == [1.0, 0.0, 0.0]:
            if not(self.rot[0] == alpha):
                self.mesh.rotate(vector, alpha-self.rot[0])
                self.parent.save_change(self, 'rotation', [vector, alpha-self.rot[0]])
                self.rot[0] = alpha
        elif vector.tolist() == [0.0, 1.0, 0.0]:
            if not(self.rot[1] == alpha):
                self.mesh.rotate(vector, alpha-self.rot[1])
                self.parent.save_change(self, 'rotation', [vector, alpha-self.rot[1]])
                self.rot[1] = alpha
        elif vector.tolist() == [0.0, 0.0, 1.0]:
            if not(self.rot[2] == alpha):
                self.mesh.rotate(vector, alpha-self.rot[2])
                self.parent.save_change(self, 'rotation', [vector, alpha-self.rot[2]])
                self.rot[2] = alpha
        self.mesh.update_min()
        self.mesh.update_max()

        self.min = self.mesh.min_
        self.max = self.mesh.max_
        self.min_scene = self.mesh.min_ + self.pos
        self.max_scene = self.mesh.max_ + self.pos

        #self.place_on_zero()

    def set_scale(self, value):
        #TODO:Omezeni minimalni velikosti
        scale_coef = value[0]/(numpy.linalg.norm(self.max)*0.5)
        scale_coef = numpy.array([scale_coef, scale_coef, scale_coef])
        #if not(self.scale[0] == value[0] and self.scale[1] == value[1] and self.scale[2] == value[2]):
        if not(self.scale[0] == scale_coef[0] and self.scale[1] == scale_coef[1] and self.scale[2] == scale_coef[2]):
            #self.mesh.vectors *= scale_coef/self.scale
            self.mesh.vectors *= scale_coef
            self.parent.save_change(self, 'scale', [scale_coef])
            #self.scale = value
            self.scale = scale_coef
            self.mesh.update_min()
            self.mesh.update_max()

            self.min = self.mesh.min_
            self.max = self.mesh.max_

            self.min_scene = self.mesh.min_ + self.pos
            self.max_scene = self.mesh.max_ + self.pos

            self.place_on_zero()


    def make_change(self, do, change_type, data):
        if do:
            direction = 1.
        else:
            direction = -1.0

        if change_type == 'move':
            print("undo move")
            self.set_move(data[0]*direction)
        elif change_type == 'rotation':
            print("undo rotation")
            self.set_rotation(data[0], data[1]*direction)
        elif change_type == 'scale':
            print("undo scale")
            #TODO:Je jeste potreba doplnit pokladani na podlozku
            #TODO:Skontrolovat koeficient scalu-jestli nebude potreba ho nejak prepocitat
            self.set_scale(data[0])





    def place_on_zero(self):
        min = self.min_scene
        max = self.max_scene
        pos = self.pos

        if min[2] < 0.0:
            diff = min[2] * -1.0
            pos[2]+=diff
            self.pos = pos
        elif min[2] > 0.0:
            diff = min[2] * -1.0
            pos[2]+=diff
            self.pos = pos

        self.min_scene = self.min + pos
        self.max_scene = self.max + pos


    def update_position(self):
        self.update_min_max()
        if self.min[2] < 0.:
            len = self.min[2] * -1.0
            self.pos[2]+=len
            self.update_min_max()

    def update_min_max(self):
        self.mesh.update_min()
        self.mesh.update_max()
        self.min = self.mesh.min_
        self.max = self.mesh.max_

        self.min_scene = self.min + self.pos
        self.max_scene = self.max + self.pos




class ModelTypeAbstract(object):
    '''
    model type is abstract class, reprezenting reading of specific model data file
    '''
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def load(self, filename):
        logging.debug("This is abstract model type")

        return None


class ModelTypeStl(ModelTypeAbstract):
    '''
    Concrete ModelType class for STL type file, it can load binary and char file
    '''

    def load(self, filename):
        logging.debug("this is STL file reader")
        mesh = Mesh.from_file(filename)
        return ModelTypeStl.load_from_mesh(mesh, filename, True)

    @staticmethod
    def load_from_mesh(mesh, filename="", normalize=True):
        model = Model()

        if filename:
            model.filename = basename(filename)
        else:
            model.filename = ""

        '''
        some magic with model data...
        I need normals, transformations...
        '''
        #model.normal = [[nor[0]/numpy.linalg.norm(nor), nor[1]/numpy.linalg.norm(nor), nor[2]/numpy.linalg.norm(nor)] for nor in mesh.normals]
        #mesh.normals = numpy.array([i/numpy.linalg.norm(i) for i in mesh.normals])

        #mesh.normals /= numpy.sqrt(numpy.einsum('...i,...i', mesh.normals, mesh.normals))
        mesh.normals /= numpy.sqrt((mesh.normals ** 2).sum(-1))[..., numpy.newaxis]

        #model.normal = mesh.normals

        #scale of imported data
        mesh.points *= model.scaleDefault[0]

        mesh.update_max()
        mesh.update_min()
        #model.recalculate_min_max()

        #calculate min and max for BoundingBox and center of object
        model.max = mesh.max_
        model.min = mesh.min_

        model.boundingSphereCenter[0] = (model.max[0] + model.min[0]) * .5
        model.boundingSphereCenter[1] = (model.max[1] + model.min[1]) * .5
        model.boundingSphereCenter[2] = (model.max[2] + model.min[2]) * .5

        model.zeroPoint = deepcopy(model.boundingSphereCenter)
        model.zeroPoint[2] = model.min[2]

        model.mesh = mesh

        #normalize position of object on 0
        if normalize:
            model.normalize_object()

        max_l = numpy.linalg.norm(mesh.max_)
        min_l = numpy.linalg.norm(mesh.min_)
        if max_l > min_l:
            model.boundingSphereSize = max_l
        else:
            model.boundingSphereSize = min_l

        model.min_scene = model.min + model.pos
        model.max_scene = model.max + model.pos

        #model.displayList = model.make_display_list()

        return model


def intersection_ray_plane(start, end, pos=[.0, .0, .0], n=[.0, .0, 1.]):
    r = ray.create_from_line(line.create_from_points(start, end))
    res = geometric_tests.ray_intersect_plane(r, plane.create_from_position(pos, n))
    return res


#math
class Vector(object):
    def __init__(self, v=[.0, .0, .0], a=[], b=[]):
        if a and b:
            self.x = b[0]-a[0]
            self.y = b[1]-a[1]
            self.z = b[2]-a[2]
        else:
            self.x = v[0]
            self.y = v[1]
            self.z = v[2]


    def minus(self, v):
        self.x -= v[0]
        self.y -= v[1]
        self.z -= v[2]

    def sqrt(self, n):
        self.x /= n
        self.y /= n
        self.z /= n

    def plus(self, v):
        self.x += v[0]
        self.y += v[1]
        self.z += v[2]

    def normalize(self):
        l = self.len()
        self.x /= l
        self.y /= l
        self.z /= l

    def lenght(self, v):
        x = v[0] - self.x
        y = v[1] - self.y
        z = v[2] - self.z
        return math.sqrt((x*x)+(y*y)+(z*z))

    def len(self):
        x = self.x
        y = self.y
        z = self.z
        return math.sqrt((x*x)+(y*y)+(z*z))

    def getRaw(self):
        return [self.x, self.y, self.z]

    @staticmethod
    def minusAB(a, b):
        c =[0,0,0]
        c[0] = a[0]-b[0]
        c[1] = a[1]-b[1]
        c[2] = a[2]-b[2]
        return c