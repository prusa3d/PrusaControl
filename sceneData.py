# -*- coding: utf-8 -*-
import numpy
from abc import ABCMeta, abstractmethod

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
    def __init__(self):
        self.hot_bed_dimension = {'type':'cube',
                                'a':25,
                                'b':25,
                                'c':25}
        self.model_position_offset = 10.

        self.sceneZero = [.0, .0, .0]
        self.models = []

    def clearScene(self):
        self.models = []

    def automatic_models_position(self):
        logging.info('Automaticke rozhazeni modelu po scene')
        #sort objects over size of bounding sphere
        self.models = sorted(self.models, key=lambda k: k.boundingSphereSize, reverse=True)
        #place biggest object(first one) on center
        #place next object in array on place around center(in clockwise direction) on place zero(center) + 1st object size/2 + 2nd object size/2 + offset
        for i, m in enumerate(self.models):
            self.find_new_position(i, m)


    #TODO:Iteratible adding models and finding new possition
    def find_new_position(self, index, model):
        position_vector = [.0, .0, .0]
        scene_tmp = self.models[:index]
        if index == 0:
            scene_tmp[index].pos = position_vector
        else:
            while not model.intersection_model_list_model_(scene_tmp):
                #TODO:Nejak postavit to ze se vezme pozice stredu a zacne se pridavat v soustrednych kruzich do te doby dokud se nenajde misto
                #position_vector[0] += cos()
                #position_vector[1] += sin()

                model.pos = position_vector





    #TODO:Doplnit setovani hot_bed dimension from settings->controller
    def define_hot_bed(self, param):
        pass





class Model(object):
    '''
    this is reprezentation of model data, data readed from file
    '''
    def __init__(self):
        #structural data
        self.v0 = []
        self.v1 = []
        self.v2 = []

        self.dataTmp = []

        #self.normal = []
        self.normal = []
        self.displayList = []

        #transformation data
        self.pos = [.0,.0,.0]
        self.rot = [.0,.0,.0]
        self.scale = [1.,1.,1.]
        self.scaleDefault = [.1,.1,.1]

        #helping data
        self.selected = False
        self.boundingSphereSize = .0
        self.boundingSphereCenter = [.0, .0, .0]
        self.boundingBox = []
        self.boundingMinimalPoint = [.0, .0, .0]
        self.zeroPoint = [.0, .0, .0]
        self.min = [.0,.0,.0]
        self.max = [.0,.0,.0]

        self.color = [randint(3, 8) * 0.1,
                      randint(3, 8) * 0.1,
                      randint(3, 8) * 0.1]



    def closestPoint(self, a, b, p):
        ab = Vector([b.x-a.x, b.y-a.y, b.z-a.z])
        abSquare = numpy.dot(ab.getRaw(), ab.getRaw())
        ap = Vector([p.x-a.x, p.y-a.y, p.z-a.z])
        apDotAB = numpy.dot(ap.getRaw(), ab.getRaw())
        t = apDotAB / abSquare
        q = Vector([a.x+ab.x*t, a.y+ab.y*t, a.z+ab.z*t])
        return q

    def intersectionRayBoundingSphere(self, start, end):
        v = Vector3(self.boundingSphereCenter)
        matrix = Matrix44.from_scale(Vector3(self.scale))
        matrix = matrix * Matrix44.from_translation(Vector3(self.pos))

        v = matrix * v

        pt = self.closestPoint(Vector(start), Vector(end), Vector(v.tolist()))
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

    def intersectionRayModel(self, rayStart, rayEnd):
        self.dataTmp = itertools.izip(self.v0, self.v1, self.v2)
        matrix = Matrix44.from_scale(Vector3(self.scale))
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


    def normalizeObject(self):
        sceneCenter = Vector(a=Vector().getRaw(), b=self.zeroPoint)
        self.v0 = [ Vector().minusAB(v, sceneCenter.getRaw())  for v in self.v0]
        self.v1 = [ Vector().minusAB(v, sceneCenter.getRaw())  for v in self.v1]
        self.v2 = [ Vector().minusAB(v, sceneCenter.getRaw())  for v in self.v2]

        self.max = Vector().minusAB(self.max, sceneCenter.getRaw())
        self.min = Vector().minusAB(self.min, sceneCenter.getRaw())

        self.boundingSphereCenter = Vector().minusAB(self.boundingSphereCenter, sceneCenter.getRaw())
        self.zeroPoint = Vector().minusAB(self.zeroPoint, sceneCenter.getRaw())
        self.zeroPoint[2] = self.min[2]


    def render(self, debug=False):
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        if debug:
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

        if self.selected:
            glColor3f(.5,0,0)
        else:
            glColor3f(self.color[0], self.color[1], self.color[2])

        glCallList(self.displayList)
        glPopMatrix()


    def makeDisplayList(self):
        genList = glGenLists(1)
        glNewList(genList, GL_COMPILE)

        glBegin(GL_TRIANGLES)
        for i in xrange(len(self.v0)):
            glNormal3fv(self.normal[i])
            glVertex3fv(self.v0[i])
            glVertex3fv(self.v1[i])
            glVertex3fv(self.v2[i])
        glEnd()
        glEndList()

        return genList

    def __str__(self):
        return "Size: %s" % self.boundingSphereSize


class ModelTypeAbstract(object):
    '''
    model type is abstract class, reprezenting reading of specific model data file
    '''
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def load(filename):
        print "This is abstract model type"
        return None



class ModelTypeStl(ModelTypeAbstract):
    '''
    Concrete ModelType class for STL type file, it can load binary and char file
    '''

    def load(self, filename):
        print "this is STL file reader"
        mesh = Mesh.from_file(filename)
        model = Model()

        '''
        some magic with model data...
        I need normals, transformations...
        '''
        #normalization of normal vectors
        #mesh.update_normals()

        model.normal = [[nor[0]/numpy.linalg.norm(nor), nor[1]/numpy.linalg.norm(nor), nor[2]/numpy.linalg.norm(nor)] for nor in mesh.normals]

        #scale of imported data
        model.v0 = mesh.v0*model.scaleDefault[0]
        model.v1 = mesh.v1*model.scaleDefault[1]
        model.v2 = mesh.v2*model.scaleDefault[2]

        #TODO:Zrychlit tuto cast
        #calculate min and max for BoundingBox and center of object
        model.max[0] = numpy.max([a[0] for a in itertools.chain(model.v0, model.v1, model.v2)])
        model.min[0] = numpy.min([a[0] for a in itertools.chain(model.v0, model.v1, model.v2)])
        model.boundingSphereCenter[0] = (model.max[0] + model.min[0]) * .5

        model.max[1] = numpy.max([a[1] for a in itertools.chain(model.v0, model.v1, model.v2)])
        model.min[1] = numpy.min([a[1] for a in itertools.chain(model.v0, model.v1, model.v2)])
        model.boundingSphereCenter[1] = (model.max[1] + model.min[1]) * .5

        model.max[2] = numpy.max([a[2] for a in itertools.chain(model.v0, model.v1, model.v2)])
        model.min[2] = numpy.min([a[2] for a in itertools.chain(model.v0, model.v1, model.v2)])
        model.boundingSphereCenter[2] = (model.max[2] + model.min[2]) * .5

        model.zeroPoint = deepcopy(model.boundingSphereCenter)
        model.zeroPoint[2] = model.min[2]

        #normalize position of object on 0
        model.normalizeObject()

        #calculate size of BoundingSphere
        v = Vector(model.boundingSphereCenter)
        for vert in itertools.chain(model.v0, model.v1, model.v2):
            vL = abs(v.lenght(vert))
            if vL > model.boundingSphereSize:
                model.boundingSphereSize = vL

        model.pos = [randint(0, 10), randint(0, 10), 0]

        model.displayList = model.makeDisplayList()

        return model

def intersectionRayPlane(start, end, p=[]):
    r = ray.create_from_line(line.create_from_points(start, end))
    v = [.0,.0,.0]
    n = [.0,.0,1.]
    res = geometric_tests.ray_intersect_plane(r, plane.create_from_position(v, n))
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