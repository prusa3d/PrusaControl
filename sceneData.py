# -*- coding: utf-8 -*-
import numpy
from abc import ABCMeta, abstractmethod
from os.path import basename

from PyQt4.QtCore import QObject
from pyrr.plane import position
from stl.mesh import Mesh
from random import randint
import math
import itertools

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from copy import deepcopy
from pyrr import Matrix44, Vector3, geometric_tests, line, ray, plane



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
            return
        scene_tmp = self.models[:index]
        if index > 0:
            while model.intersection_model_list_model_(scene_tmp):
                for angle in xrange(0, 360, 20):
                    model.pos[0] = math.cos(math.radians(angle)) * (position_vector[0])
                    model.pos[1] = math.sin(math.radians(angle)) * (position_vector[1])

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

        #transformation data
        self.pos = [.0, .0, .0]
        self.rot = [.0, .0, .0]
        self.scale = [1., 1., 1.]
        self.scaleDefault = [.1, .1, .1]

        self.matrix = Matrix44([[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]])

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
        m = Matrix44().from_translation(self.pos)
        x = Matrix44().from_x_rotation(self.rot[0])
        y = Matrix44().from_y_rotation(self.rot[1])
        z = Matrix44().from_z_rotation(self.rot[2])
        s = Matrix44().from_scale(self.scale)

        f = s * x * y * z * m

        #TODO:Wrong, by transformation matrix multiply vertex data and recalculate min, max
        min = f * Vector3(self.min)
        max = f * Vector3(self.max)

        if max[0] <= (printer['printing_space'][0]*.5) and min[0] >= (printer['printing_space'][0]*-.5) and max[1] <= (printer['printing_space'][1]*.5)\
                and min[1] >= (printer['printing_space'][1]*-.5) and max[2] <= (printer['printing_space'][2]*.5) \
                and min[2] >= (printer['printing_space'][2]*-.5):
            return True
        else:
            return False

    def get_mesh(self):
        #New style
        #self.v0 = self.mesh.v0
        #self.v1 = self.mesh.v1
        #self.v2 = self.mesh.v2
        print('saving model')

        #data = numpy.zeros(len(self.v0), dtype=Mesh.dtype)
        #scale = numpy.array(self.scaleDefault)
        #move = numpy.array(self.pos)
        #moveM = Matrix44().from_translation(self.pos)
        #rotateXM = Matrix44().from_x_rotation(math.radians(self.rot[0]))
        #rotateYM = Matrix44().from_y_rotation(math.radians(self.rot[1]))
        #rotateZM = Matrix44().from_z_rotation(math.radians(self.rot[2]))
        #scaleM = Matrix44().from_scale(self.scale)
        #scaleDM = Matrix44().from_scale(self.scaleDefault)

        #r = rotateXM * rotateYM * rotateZM

        #f = scaleM * ~r * moveM * ~scaleDM

        data = numpy.zeros(len(self.mesh.vectors), dtype=Mesh.dtype)

        mesh = deepcopy(self.mesh)

        mesh.update_min()
        mesh.update_max()

        mesh.vectors *= numpy.array(self.scale)

        mesh.rotate([1., .0, .0], self.rot[0])
        mesh.rotate([.0, 1., .0], self.rot[1])
        mesh.rotate([.0, .0, 1.], self.rot[2])

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
        matrix = Matrix44.from_scale(Vector3(self.scale))
        matrix = matrix * Matrix44.from_translation(Vector3(self.pos))

        v = matrix * v

        pt = self.closest_point(Vector(start), Vector(end), Vector(v.tolist()))
        lenght = pt.lenght(v.tolist())
        return lenght < self.boundingSphereSize

    def intersection_model_model(self, model):
        vector_model_model = Vector(a=model.pos, b=self.pos)
        distance = vector_model_model.len()
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
        matrix = Matrix44.from_scale(Vector3(self.scale))
        #TODO:Add rotation
        matrix = matrix * Matrix44.from_translation(Vector3(self.pos))

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
        self.boundingSphereCenter = self.boundingSphereCenter.tolist()

        self.zeroPoint = numpy.array(self.zeroPoint) + r
        self.zeroPoint[2] = self.min[2]

        self.pos = numpy.array([.0, .0, .0]) + self.zeroPoint
        self.pos = self.pos.tolist()

        self.zeroPoint = self.zeroPoint.tolist()

        self.normalization_flag = True


    def render(self, picking=False, debug=False):
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        #glEnable(GL_VERTEX_ARRAY)
        #glEnable(GL_NORMAL_ARRAY)
        if debug and not picking:
            glDisable(GL_DEPTH_TEST)

            glBegin(GL_POINTS)
            glColor3f(0,1,0)
            glVertex3f(self.boundingSphereCenter[0], self.boundingSphereCenter[1], self.boundingSphereCenter[2])
            glColor3f(0,0,1)
            glVertex3f(self.zeroPoint[0], self.zeroPoint[1], self.zeroPoint[2])
            glEnd()
            glEnable(GL_DEPTH_TEST)
            glPushMatrix()
            glTranslated(self.boundingSphereCenter[0], self.boundingSphereCenter[1], self.boundingSphereCenter[2])
            glLineWidth(1)
            glColor3f(.25, .25, .25)
            glutWireSphere(self.boundingSphereSize+0.1, 16, 10)
            glPopMatrix()

        if picking:
            glColor3ubv(self.colorId)
        else:
            if self.is_in_printing_space(self.parent.controller.actual_printer):
                glColor3fv(self.color)
            else:
                glColor3f(1., .0, .0)

        glRotatef(self.rot[0], 1., 0., 0.)
        glRotatef(self.rot[1], 0., 1., 0.)
        glRotatef(self.rot[2], 0., 0., 1.)

        glScalef(self.scale[0], self.scale[1], self.scale[2])

        #glEnable(GL_NORMALIZE)
        glCallList(self.displayList)
        #glDisable(GL_NORMALIZE)
        #glDisable(GL_VERTEX_ARRAY)
        #glDisable(GL_NORMAL_ARRAY)
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

    '''
    def recalculate_min_max(self):
        #TODO:
        #transform vertex data from mesh to actual matrix
        #recalculate min and max for bounding box
        #tats all

        #calculate min and max for BoundingBox and center of object
        #self.max[0] = numpy.max([a[0] for a in itertools.chain(self.v0, self.v1, self.v2)])
        #self.min[0] = numpy.min([a[0] for a in itertools.chain(self.v0, self.v1, self.v2)])

        self.boundingSphereCenter[0] = (self.max[0] + self.min[0]) * .5

        self.max[1] = numpy.max([a[1] for a in itertools.chain(self.v0, self.v1, self.v2)])
        self.min[1] = numpy.min([a[1] for a in itertools.chain(self.v0, self.v1, self.v2)])
        self.boundingSphereCenter[1] = (self.max[1] + self.min[1]) * .5

        self.max[2] = numpy.max([a[2] for a in itertools.chain(self.v0, self.v1, self.v2)])
        self.min[2] = numpy.min([a[2] for a in itertools.chain(self.v0, self.v1, self.v2)])
        self.boundingSphereCenter[2] = (self.max[2] + self.min[2]) * .5
    '''

    def update_min_max(self):
        self.mesh.update_min()
        self.mesh.update_max()
        self.min = self.mesh.min_
        self.min = self.mesh.max_



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
        print("normalizace")

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


        model.displayList = model.make_display_list()

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