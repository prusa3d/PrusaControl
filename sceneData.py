# -*- coding: utf-8 -*-
import numpy as np
from abc import ABCMeta, abstractmethod
from os.path import basename

from PyQt4.QtCore import QObject
from stl.mesh import Mesh
from random import randint
import math
import itertools
from pprint import pprint


import OpenGL
OpenGL.ERROR_CHECKING = False
OpenGL.ERROR_LOGGING = False

from OpenGL.GL import *
#from OpenGL.GLU import *
#from OpenGL.GLUT import *

from copy import deepcopy
from pyrr import matrix44, Vector3, geometric_tests, line, ray, plane, matrix33

#glutInit()

class AppScene(object):
    '''
    Class holding data of scene, models, positions, parameters
    it can be used for generating sliced data and rendering data
    '''
    def __init__(self, controller):
        self.controller = controller
        self.model_position_offset = 0.1

        self.sceneZero = [.0, .0, .0]
        self.models = []
        self.printable = True
        self.camera_vector = np.array([0.,0.,0.])

        self.transformation_list = []
        self.actual_list_position = 0

        self.analyze_result_data_tmp = []


    def save_change(self, old_instance):
        if self.actual_list_position < len(self.transformation_list)-1:
            self.transformation_list = self.transformation_list[:self.actual_list_position+1]

        self.transformation_list.append([old_instance, np.copy(old_instance.scale_matrix), np.copy(old_instance.rotation_matrix), np.copy(old_instance.pos)])
        self.actual_list_position = len(self.transformation_list)-1
        #self.controller.show_message_on_status_bar("Set state %s from %s" % ('{:2}'.format(self.actual_list_position), '{:2}'.format(len(self.transformation_list))))

    def make_undo(self):
        #just move pointer of transformation to -1 or leave on 0
        if self.actual_list_position >= 1:
            self.actual_list_position -= 1
            old_instance, scale, rot, pos = self.transformation_list[self.actual_list_position]
            old_instance.scale_matrix = np.copy(scale)
            old_instance.rotation_matrix = np.copy(rot)
            old_instance.pos = deepcopy(pos)
            old_instance.is_changed = True
            #self.controller.show_message_on_status_bar("Set state %s from %s" % ('{:2}'.format(self.actual_list_position), '{:2}'.format(len(self.transformation_list))))

    def make_do(self):
        #move pointer of transformation to +1 or leave on last
        if self.actual_list_position < len(self.transformation_list)-1:
            self.actual_list_position += 1
            old_instance, scale, rot, pos = self.transformation_list[self.actual_list_position]
            old_instance.scale_matrix = np.copy(scale)
            old_instance.rotation_matrix = np.copy(rot)
            old_instance.pos = deepcopy(pos)
            old_instance.is_changed = True
            #self.controller.show_message_on_status_bar("Set state %s from %s" % ('{:2}'.format(self.actual_list_position), '{:2}'.format(len(self.transformation_list))))

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

    @staticmethod
    def get_area_of_triangle(triangle):
        a = np.linalg.norm(triangle[2]-triangle[1])
        b = np.linalg.norm(triangle[2]-triangle[0])
        c = np.linalg.norm(triangle[1]-triangle[0])
        s = (a+b+c)/2.
        area_tmp = s*((s-a)*(s-b)*(s-c))
        area = np.sqrt(area_tmp)

        return area

    def get_contact_faces_with_area_smaller_than(self, area_size):
        whole_scene = self.get_whole_scene_in_one_mesh()


        b= whole_scene.vectors[:, :, 2] < 0.1
        print(str(b))
        b_tmp = np.array([i.all() for i in b])
        print(str(b_tmp))
        tmp_brim = whole_scene.vectors[b_tmp]
        print(str(tmp_brim))

        #tmp_brim = np.array([i+whole_scene.normals[n]*0.001 for n, i in enumerate(whole_scene.vectors) if (i[0][2]<0.1 and i[1][2]<0.1 and i[2][2]<0.1)])

        whole_scene.update_max()
        whole_scene.update_min()

        boundingSphereCenter = np.array([0., 0., 0.])
        boundingSphereCenter[0] = (whole_scene.max_[0] + whole_scene.min_[0]) * .5
        boundingSphereCenter[1] = (whole_scene.max_[1] + whole_scene.min_[1]) * .5
        boundingSphereCenter[2] = (whole_scene.max_[2] + whole_scene.min_[2]) * .5

        max_l = np.linalg.norm(whole_scene.max_)
        min_l = np.linalg.norm(whole_scene.min_)
        if max_l > min_l:
            boundingSphereSize = max_l
        else:
            boundingSphereSize = min_l

        object_space = 4.189*(boundingSphereSize*.5)**3

        areas = [AppScene.get_area_of_triangle(i) for i in tmp_brim]
        connection_area = np.sum(areas)

        if not len(tmp_brim) == 0:
            tmp_brim *= np.array([.1, .1, .1])

        if connection_area == 0:
            brim = True
        elif object_space/connection_area <= 300.:
            brim = False
        else:
            brim = True

        if len(self.analyze_result_data_tmp) == 0 and len(tmp_brim) == 0:
            self.analyze_result_data_tmp = []
        elif len(self.analyze_result_data_tmp) == 0:
            self.analyze_result_data_tmp = tmp_brim
        elif not (len(tmp_brim) == 0) and not (len(self.analyze_result_data_tmp) == 0):
            np.concatenate((tmp_brim, self.analyze_result_data_tmp), axis=0)

        return brim


    def get_faces_by_smaller_angel_normal_and_vector(self, vector, angle):
        #calculate angel between normal vector and given vector
        #return list of faces with smaller
        whole_scene = self.get_whole_scene_in_one_mesh()
        d = 0.1
        self.analyze_result_data_tmp = np.array([])
        self.analyze_result_data_tmp = np.array([i+whole_scene.normals[n]*d for n, i in enumerate(whole_scene.vectors) if AppScene.calc_angle(whole_scene.normals[n], vector) <= 90.-angle ])
        self.analyze_result_data_tmp = np.array([i for n, i in enumerate(self.analyze_result_data_tmp) if not (i[0][2]<0.1 and i[1][2]<0.1 and i[2][2]<0.1) and AppScene.is_length_in_z_bigger_then(i, 0.75)])

        if not len(self.analyze_result_data_tmp) == 0:
            self.analyze_result_data_tmp *= np.array([.1, .1, .1])

        return self.analyze_result_data_tmp

    @staticmethod
    def calc_angle(normal, vector):
        normal /= np.linalg.norm(normal)
        vector /= np.linalg.norm(vector)
        cos_ang = np.dot(normal, vector)
        sin_ang = np.linalg.norm(np.cross(normal, vector))
        deg = np.degrees(np.arctan2(sin_ang, cos_ang))
        return deg

    @staticmethod
    def is_length_in_z_bigger_then(triangle, minimal_z):
        max_z = max([i[2] for i in triangle])
        min_z = min([i[2] for i in triangle])
        length = max_z - min_z
        if length >= minimal_z:
            return True
        else:
            return False

    def delete_selected_models(self):
        delete = False
        print("N: " + str(len(self.models)) + ' ' + str(self.models))
        temp = []
        for m in self.models:
            if m.selected:
                temp.append(m)
                delete = True

        for t in temp:
            self.models.remove(t)
            print("Deleted")
        print("N: " + str(len(self.models)) + ' ' + str(self.models))

        if delete:
            self.controller.view.update_scene()


    def clearScene(self):
        self.models = []
        self.transformation_list = []
        self.actual_list_position = 0

    def clear_selected_models(self):
        for model in self.models:
            model.selected = False

    def automatic_models_position(self):
        #sort objects over size of bounding sphere

        #self.models = sorted(self.models, key=lambda k: k.boundingSphereSize, reverse=True)
        self.models = sorted(self.models, key=lambda k: np.linalg.norm(k.size), reverse=True)
        #place biggest object(first one) on center
        #place next object in array on place around center(in clockwise direction) on place zero(center) + 1st object size/2 + 2nd object size/2 + offset
        for i, m in enumerate(self.models):
            self.find_new_position(i, m)

    def find_new_position(self, index, model):
        position_vector = [.0, .0]
        if index == 0:
            self.models[0 ].pos[0] = position_vector[0]
            self.models[0].pos[1] = position_vector[1]

            self.models[0].max_scene = self.models[0].max + self.models[0].pos
            self.models[0].min_scene = self.models[0].min + self.models[0].pos
            return
        scene_tmp = self.models[:index]
        if index > 0:
            while model.intersection_model_list_model_(scene_tmp):
                #for angle in xrange(0, 360, 20):
                for angle in xrange(0, 360, 5):
                    model.pos[0] = math.cos(math.radians(angle)) * (position_vector[0])
                    model.pos[1] = math.sin(math.radians(angle)) * (position_vector[1])

                    model.max_scene = model.max + model.pos
                    model.min_scene = model.min + model.pos

                    #TODO:Add some test for checking if object is inside of printing space of printer
                    if not model.intersection_model_list_model_(scene_tmp):
                        return

                position_vector[0] += model.boundingSphereSize*.1
                position_vector[1] += model.boundingSphereSize*.1

    def get_whole_scene_in_one_mesh(self):
        return Mesh(np.concatenate([i.get_mesh().data for i in self.models]))

    def save_whole_scene_to_one_stl_file(self, filename):
        whole_scene = self.get_whole_scene_in_one_mesh()
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
        self.temp_mesh = None

        #transformation data, connected to scene
        self.pos = np.array([.0, .0, .0])
        self.pos_old = np.array([.0, .0, .0])
        self.rot = np.array([.0, .0, .0])
        self.rot_scene = np.array([.0, .0, .0])
        self.scale = np.array([1., 1., 1.])
        self.scaleDefault = [.1, .1, .1]
        self.min_scene = [.0, .0, .0]
        self.max_scene = [.0, .0, .0]

        self.scale_matrix = np.array([[ 1.,  0.,  0.],
                                            [ 0.,  1.,  0.],
                                            [ 0.,  0.,  1.]])
        self.temp_scale = np.array([[ 1.,  0.,  0.],
                                            [ 0.,  1.,  0.],
                                            [ 0.,  0.,  1.]])

        self.rotation_matrix = np.array([[ 1.,  0.,  0.],
                                            [ 0.,  1.,  0.],
                                            [ 0.,  0.,  1.]])
        self.temp_rotation = np.array([[ 1.,  0.,  0.],
                                            [ 0.,  1.,  0.],
                                            [ 0.,  0.,  1.]])

        self.tiled_normals = np.array([])

        #helping data
        self.selected = False
        self.boundingSphereSize = .0
        self.boundingSphereCenter = np.array([.0, .0, .0])
        self.boundingBox = []
        self.boundingMinimalPoint = [.0, .0, .0]
        self.zeroPoint = np.array([.0, .0, .0])
        self.min = [.0, .0, .0]
        self.max = [.0, .0, .0]
        self.size = np.array([.0, .0, .0])
        self.size_origin = np.array([.0, .0, .0])

        #self.color = [75./255., 119./255., 190./255.]
        self.color = [34./255., 167./255., 240./255.]

        #status of object
        self.is_changed = True

        #source file data
        #example car.stl
        self.filename = ""
        self.normalization_flag = False

    def clear_state(self):
        self.is_changed = False

    def changing(self):
        self.is_changed = True

    def is_in_printing_space(self, printer):
        min = self.min_scene
        max = self.max_scene

        if max[0] <= (printer['printing_space'][0]*.5) and min[0] >= (printer['printing_space'][0]*-.5):
                if max[1] <= (printer['printing_space'][1]*.5) and min[1] >= (printer['printing_space'][1]*-.5):
                    if max[2] <= printer['printing_space'][2] and min[2] >= -0.1:
                        self.parent.controller.set_printable(True)
                        return True
                    else:
                        #print("naruseni v Z")
                        self.parent.controller.set_printable(False)
                        return False
                else:
                    #print("naruseni v Y")
                    self.parent.controller.set_printable(False)
                    return False
        else:
            #print("naruseni v X")
            self.parent.controller.set_printable(False)
            return False

    def get_mesh(self, transform=True):
        data = np.zeros(len(self.mesh.vectors), dtype=Mesh.dtype)

        mesh = Mesh(self.temp_mesh.data.copy())

        if transform:
            mesh.vectors += np.array(self.pos)

        mesh.vectors /= np.array(self.scaleDefault)

        data['vectors'] = mesh.vectors

        mesh.update_min()
        mesh.update_max()

        return Mesh(data)


    def normalize_object(self):
        r = np.array([.0, .0, .0]) - np.array(self.boundingSphereCenter)

        self.mesh.vectors = self.mesh.vectors + r

        self.update_min_max()
        self.boundingSphereCenter = np.array(self.boundingSphereCenter) + r

        self.zeroPoint = np.array(self.zeroPoint) + r
        self.zeroPoint[2] = self.min[2]

        self.pos = np.array([.0, .0, .0]) - self.zeroPoint

        self.normalization_flag = True


    def set_move(self, vector, add=True):
        #TODO:Add units in message(US inches, EU cm, ...)
        vector = np.array(vector)
        if add:
            self.pos += vector
        else:
            self.pos = vector
        self.parent.controller.show_message_on_status_bar("Place on %s %s" % ('{:.2}'.format(self.pos[0]), '{:.2}'.format(self.pos[1])))
        self.min_scene = self.min + self.pos
        self.max_scene = self.max + self.pos


    def set_rotation(self, vector, alpha):
        if vector.tolist() == [1.0, 0.0, 0.0]:
            self.temp_rotation = Mesh.rotation_matrix(vector, alpha)
            self.parent.controller.show_message_on_status_bar("Angle X: " + str(np.degrees(alpha)))
        elif vector.tolist() == [0.0, 1.0, 0.0]:
            self.temp_rotation = Mesh.rotation_matrix(vector, alpha)
            self.parent.controller.show_message_on_status_bar("Angle Y: " + str(np.degrees(alpha)))
        elif vector.tolist() == [0.0, 0.0, 1.0]:
            self.temp_rotation = Mesh.rotation_matrix(vector, alpha)
            self.parent.controller.show_message_on_status_bar("Angle Z: " + str(np.degrees(alpha)))

        self.mesh.update_min()
        self.mesh.update_max()

        self.min = self.mesh.min_
        self.max = self.mesh.max_
        self.min_scene = self.mesh.min_ + self.pos
        self.max_scene = self.mesh.max_ + self.pos

        self.is_changed = True

    def make_normals(self):
        self.tiled_normals = np.tile(self.temp_mesh.normals, 3)

    def apply_rotation(self):
        self.rotation_matrix = np.dot(self.rotation_matrix, self.temp_rotation)
        self.temp_rotation = np.array([[ 1.,  0.,  0.],
                                        [ 0.,  1.,  0.],
                                        [ 0.,  0.,  1.]])

    def set_scale(self, value):
        printing_space = self.parent.controller.actual_printer['printing_space']
        new_size = np.dot(self.size_origin, self.scale_matrix*value)
        if new_size[0] < printing_space[0]*0.98 and new_size[1] < printing_space[1]*0.98 and new_size[2] < printing_space[2]*0.98 and new_size[0] > 0.5 and new_size[1] > 0.5 and new_size[2] > 0.5:
            self.temp_scale = np.array([[ 1.,  0.,  0.],
                                        [ 0.,  1.,  0.],
                                        [ 0.,  0.,  1.]]) * value
            self.is_changed = True


    def apply_scale(self):
        self.scale_matrix = np.dot(self.scale_matrix, self.temp_scale)
        self.temp_scale = np.array([[ 1.,  0.,  0.],
                                        [ 0.,  1.,  0.],
                                        [ 0.,  0.,  1.]])


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

    def put_array_to_gl(self):
        glNormalPointerf(self.tiled_normals)
        glVertexPointerf(self.temp_mesh.vectors)

        #glNormalPointerf(np.tile(self.draw_mesh['normals'], 3))
        #glVertexPointerf(self.draw_mesh['vectors'])

    def render(self, picking=False, debug=False):
        glPushMatrix()
        '''
        if debug:
            #Draw BoundingBox
            #glDisable(GL_DEPTH_TEST)
            glPointSize(5)
            glBegin(GL_POINTS)
            glColor3f(1,0,0)
            glVertex3f(self.min_scene[0], self.min_scene[1], self.min_scene[2])
            glVertex3f(self.max_scene[0], self.min_scene[1], self.min_scene[2])
            glVertex3f(self.min_scene[0], self.max_scene[1], self.min_scene[2])
            glVertex3f(self.min_scene[0], self.min_scene[1], self.max_scene[2])
            glVertex3f(self.max_scene[0], self.min_scene[1], self.max_scene[2])
            glVertex3f(self.max_scene[0], self.max_scene[1], self.min_scene[2])
            glVertex3f(self.min_scene[0], self.max_scene[1], self.max_scene[2])
            glVertex3f(self.max_scene[0], self.max_scene[1], self.max_scene[2])
            glEnd()
            #glEnable(GL_DEPTH_TEST)
        '''

        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        if picking:
            glColor3ubv(self.colorId)
        else:
            if self.is_in_printing_space(self.parent.controller.actual_printer):
                if self.selected:
                    glColor3f(.75, .75, 0.)
                else:
                    glColor3fv(self.color)
            else:
                glColor3f(0.75, .0, .0)

        if self.is_changed:
            print("Changed")
            self.temp_mesh = Mesh(self.mesh.data.copy())

            final_rotation = np.dot(self.rotation_matrix, self.temp_rotation)
            final_scale = np.dot(self.temp_scale, self.scale_matrix)
            final_matrix = np.dot(final_rotation, final_scale)

            for i in range(3):
                self.temp_mesh.vectors[:, i] = self.temp_mesh.vectors[:, i].dot(final_matrix)

            self.temp_mesh.normals = self.temp_mesh.normals.dot(final_rotation)
            self.make_normals()

            self.temp_mesh.update_min()
            self.temp_mesh.update_max()

            self.min = self.temp_mesh.min_
            self.max = self.temp_mesh.max_
            self.min_scene = self.min + self.pos
            self.max_scene = self.max + self.pos

            self.place_on_zero()

            self.is_changed = False

        self.put_array_to_gl()

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        glDrawArrays(GL_TRIANGLES, 0, len(self.temp_mesh.vectors)*3)

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)

        glPopMatrix()

    def make_display_list(self):
        genList = glGenLists(1)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        glNormalPointerf(np.tile(self.mesh.normals, 3))
        glVertexPointerf(self.mesh.vectors)

        glNewList(genList, GL_COMPILE)

        glDrawArrays(GL_TRIANGLES, 0, len(self.mesh.vectors)*3)

        glEndList()

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)

        return genList

    def closest_point(self, a, b, p):
        ab = Vector([b.x-a.x, b.y-a.y, b.z-a.z])
        abSquare = np.dot(ab.getRaw(), ab.getRaw())
        ap = Vector([p.x-a.x, p.y-a.y, p.z-a.z])
        apDotAB = np.dot(ap.getRaw(), ab.getRaw())
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

    def intersection_model_model_by_BB(self, model):
        #intersection by collision of BB
        min = self.min_scene
        max = self.max_scene
        model_min = model.min_scene
        model_max = model.max_scene
        d = self.parent.model_position_offset
        return not(max[0]+d<model_min[0] or model_max[0]<min[0]-d or max[1]+d<model_min[1] or model_max[1]<min[1]-d)

    def intersection_model_model_by_BS(self, model):
        #intersection by collision of BS
        vector_model_model = self.pos - model.pos
        distance = np.linalg.norm(vector_model_model)
        if distance >= (model.boundingSphereSize+self.boundingSphereSize):
            return False
        else:
            return True

    def intersection_model_list_model_(self, list):
        for m in list:
            #if self.intersection_model_model_by_BS(m):
            if self.intersection_model_model_by_BB(m):
                return True
        return False


class ModelTypeAbstract(object):
    '''
    model type is abstract class, reprezenting reading of specific model data file
    '''
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def load(self, filename):
        #logging.debug("This is abstract model type")
        return None


class ModelTypeStl(ModelTypeAbstract):
    '''
    Concrete ModelType class for STL type file, it can load binary and char file
    '''

    def load(self, filename):
        #logging.debug("this is STL file reader")
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

        #mesh.normals /= np.sqrt(np.einsum('...i,...i', mesh.normals, mesh.normals))
        mesh.normals /= np.sqrt((mesh.normals ** 2).sum(-1))[..., np.newaxis]

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

        max_l = np.linalg.norm(mesh.max_)
        min_l = np.linalg.norm(mesh.min_)
        if max_l > min_l:
            model.boundingSphereSize = max_l
        else:
            model.boundingSphereSize = min_l

        model.min_scene = model.min + model.pos
        model.max_scene = model.max + model.pos

        model.size = model.max-model.min
        model.size_origin = deepcopy(model.size)

        model.temp_mesh = deepcopy(mesh)
        model.make_normals()

        #model.displayList = model.make_display_list()

        return model


def intersection_ray_plane(start, end, pos=np.array([.0, .0, .0]), n=np.array([.0, .0, 1.])):
    r = ray.create_from_line(line.create_from_points(start, end))
    res = geometric_tests.ray_intersect_plane(r, plane.create_from_position(-pos, n))
    return res

def intersection_ray_plane2(O, D, P=np.array([0., 0., 0.]), N=np.array([.0, .0, 1.])):
    # Return the distance from O to the intersection of the ray (O, D) with the 
    # plane (P, N), or +inf if there is no intersection.
    # O and P are 3D points, D and N (normal) are normalized vectors.
    denom = np.dot(D, N)
    if np.abs(denom) < 1e-6:
        return np.inf
    d = np.dot(P - O, N) / denom
    if d < 0:
        return np.inf
    res = D*d + O
    return np.array([res[0], res[1], res[2]])
