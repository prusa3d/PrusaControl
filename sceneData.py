# -*- coding: utf-8 -*-
import logging
from collections import defaultdict

import gc
import numpy as np
from abc import ABCMeta, abstractmethod
from os.path import basename

import time
from PyQt4.QtCore import QObject
from PyQt4.QtGui import QFont
from PyQt4.QtOpenGL import QGLBuffer
#from stl import Mode
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

from collections import namedtuple

#glutInit()

def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print('%s function took %0.3f ms' % (f.func_name, (time2-time1)*1000.0))
        return ret
    return wrap

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
        self.supports = []
        self.actual_support = []
        self.copied_models = []
        self.printable = True
        self.camera_vector = np.array([0.,0.,0.])
        self.last_selected_object = []

        self.place_offset = np.array([0., 0., 0.])

        self.transformation_list = []
        self.actual_list_position = 0

        self.analyze_result_data_tmp = []

    def save_actual_support(self):
        self.supports.append(self.actual_support)
        self.actual_support = []

    def clear_history(self):
        #print("Mazu historii")
        self.transformation_list = []
        self.actual_list_position = 0

    def save_change(self, old_instances_list):
        #print("Ukladam stav objektu")
        if self.actual_list_position < len(self.transformation_list)-1:
            self.transformation_list = self.transformation_list[:self.actual_list_position+1]

        list_of_states = [[i, deepcopy(i.isVisible), deepcopy(i.scale), deepcopy(i.rot), deepcopy(i.pos)] for i in old_instances_list]

        self.transformation_list.append(list_of_states)
        self.actual_list_position = len(self.transformation_list)-1
        #self.controller.show_message_on_status_bar("Set state %s from %s" % ('{:2}'.format(self.actual_list_position), '{:2}'.format(len(self.transformation_list))))

        #pprint(self.transformation_list)


    def make_undo(self):
        #just move pointer of transformation to -1 or leave on 0
        #print("Aktualni pozice je: " + str(self.actual_list_position))
        #pprint(self.transformation_list)
        if self.actual_list_position >= 1:
            self.actual_list_position -= 1
            list_of_states = self.transformation_list[self.actual_list_position]
            #print("Vraceny stav:")
            #pprint(list_of_states)
            for i in list_of_states:
                old_instance, isVisible, scale, rot, pos = i
                old_instance.isVisible = deepcopy(isVisible)
                old_instance.scale = deepcopy(scale)
                old_instance.rot = deepcopy(rot)
                old_instance.pos = deepcopy(pos)
                old_instance.is_changed = True
                old_instance.update_min_max()
            #self.controller.show_message_on_status_bar("Set state %s from %s" % ('{:2}'.format(self.actual_list_position), '{:2}'.format(len(self.transformation_list))))
        #print("Konec stavu")

    def make_do(self):
        #move pointer of transformation to +1 or leave on last
        #print("Aktualni pozice je: " + str(self.actual_list_position))
        #pprint(self.transformation_list)
        if self.actual_list_position < len(self.transformation_list)-1:
            #print("jsem uvnitr")
            self.actual_list_position += 1
            list_of_states = self.transformation_list[self.actual_list_position]
            for i in list_of_states:
                old_instance, isVisible, scale, rot, pos = i
                old_instance.isVisible = deepcopy(isVisible)
                old_instance.scale = deepcopy(scale)
                old_instance.rot = deepcopy(rot)
                old_instance.pos = deepcopy(pos)
                old_instance.is_changed = True
                old_instance.update_min_max()

            #self.controller.show_message_on_status_bar("Set state %s from %s" % ('{:2}'.format(self.actual_list_position), '{:2}'.format(len(self.transformation_list))))


    def calculate_support(self, pos):
        height = 25
        # self.supports.append({"pos": pos, "height": height})
        for m in self.models:
            height = self.find_support_height(m, pos)
            if height:
                self.actual_support = {"pos": pos, "height": height}
            else:
                self.actual_support = {"pos": pos, "height": 25}

    def create_support(self, pos):
        height = 25
        #self.supports.append({"pos": pos, "height": height})
        for m in self.models:
            height = self.find_support_height(m, pos)
            if height:
                self.supports.append({"pos": pos, "height": height})
                break





    def find_support_height(self, m, pos):
        ret, point = m.intersectionRayModel3(pos, np.array([pos[0], pos[1], 1.]))
        if ret:
            return np.sqrt(point.dot(point))
        else:
            return False


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

    @timing
    def get_contact_faces_with_area_smaller_than(self, area_size, whole_scene):
        #whole_scene = self.get_whole_scene_in_one_mesh()

        b= whole_scene.vectors[:, :, 2] < 0.1
        b_tmp = np.array([i.all() for i in b])
        tmp_brim = whole_scene.vectors[b_tmp]

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

    @timing
    def get_faces_by_smaller_angel_normal_and_vector(self, vector, angle, whole_scene):
        #calculate angel between normal vector and given vector
        #return list of faces with smaller
        #whole_scene = self.get_whole_scene_in_one_mesh()
        d = 0.1
        self.analyze_result_data_tmp = np.array([])
        self.analyze_result_data_tmp = np.array([i+whole_scene.normals[n]*d for n, i in enumerate(whole_scene.vectors) if AppScene.calc_angle(whole_scene.normals[n], vector) <= 90.-angle ])
        self.analyze_result_data_tmp = np.array([i for n, i in enumerate(self.analyze_result_data_tmp) if not (i[0][2]<0.1 and i[1][2]<0.1 and i[2][2]<0.1) and AppScene.is_length_in_z_bigger_then(i, 0.75)])

        if not len(self.analyze_result_data_tmp) == 0:
            self.analyze_result_data_tmp *= np.array([.1, .1, .1])

        return self.analyze_result_data_tmp

    @staticmethod
    def calc_angle(normal, vector):
        normal /= np.sqrt(normal.dot(normal))
        #normal /= np.linalg.norm(normal)
        vector /= np.sqrt(vector.dot(vector))
        #vector /= np.linalg.norm(vector)
        cos_ang = np.dot(normal, vector)
        sin_ang = np.linalg.norm(np.cross(normal, vector))
        deg = np.degrees(np.arctan2(sin_ang, cos_ang))
        return deg

    @staticmethod
    def calc_angle2(old_vec, new_vec):
        cos_ang = np.dot(old_vec, new_vec)
        cross = np.cross(old_vec, new_vec)

        neg = np.dot(cross, np.array([0., 0., 1.]))
        sin_ang = np.linalg.norm(cross) * np.sign(neg) * -1.

        alpha = np.arctan2(sin_ang, cos_ang)

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
        for m in self.models:
            if m.selected and m.isVisible:
                m.isVisible = False

        #TODO: Add state to history
        self.clear_selected_models()
        self.controller.view.update_scene()

    def copy_selected_objects(self):
        self.place_offset = np.array([0.,0.,0.])
        self.copied_models = []
        for m in self.models:
            if m.selected and m.isVisible:
                self.copied_models.append(m)

    def paste_selected_objects(self):
        self.place_offset += np.array([0.5, 0.5, 0.])
        for i in self.copied_models:
            m = deepcopy(i)
            m.set_move(self.place_offset, True, False)
            self.models.append(m)

        self.controller.update_scene()
        #self.automatic_models_position()

    #TODO:Add brim and support message
    def get_warnings(self):
        messages = []
        text00 = self.controller.view.tr("Object ")
        text01 = self.controller.view.tr(" is out of printable area!")
        for model in self.models:
            if model.isVisible:
                if not model.is_in_printing_area:
                    if len(model.filename)>7:
                        filename = model.filename[:7] + "..."
                    else:
                        filename = model.filename
                    #messages.append(u"• " + text00 + filename + text01)
                    messages.append(text00 + filename + text01)
        return messages

    def clear_scene(self):
        self.models = []
        self.transformation_list = []
        self.actual_list_position = 0

    def clear_selected_models(self):
        for m in self.models:
            m.selected = False

    def automatic_models_position(self):
        #sort objects over size of bounding sphere

        #self.models = sorted(self.models, key=lambda k: k.boundingSphereSize, reverse=True)
        self.models = sorted(self.models, key=lambda k: np.sqrt(k.size.dot(k.size)), reverse=True)

        #null position of all objects
        for m in self.models:
            zer = np.array([.0, .0, .0])
            m.pos[0] = zer[0]
            m.pos[1] = zer[1]

            m.max_scene = m.max + m.pos
            m.min_scene = m.min + m.pos

        #place biggest object(first one) on center
        #place next object in array on place around center(in clockwise direction) on place zero(center) + 1st object size/2 + 2nd object size/2 + offset
        for i, m in enumerate(self.models):
            self.find_new_position(i, m)

        self.save_change(self.models)

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
                #for angle in xrange(0, 360, 20):
                for angle in xrange(0, 360, 45):
                    model.pos[0] = math.cos(math.radians(angle)) * (position_vector[0])
                    model.pos[1] = math.sin(math.radians(angle)) * (position_vector[1])

                    model.max_scene = model.max + model.pos
                    model.min_scene = model.min + model.pos

                    #TODO:Add some test for checking if object is inside of printing space of printer
                    if not model.intersection_model_list_model_(scene_tmp):
                        return

                for angle in xrange(0, 360, 5):
                    #this angels are tried
                    if angle in [0, 45, 90, 135, 180, 225, 270, 315, 360]:
                        continue
                    model.pos[0] = math.cos(math.radians(angle)) * (position_vector[0])
                    model.pos[1] = math.sin(math.radians(angle)) * (position_vector[1])

                    model.max_scene = model.max + model.pos
                    model.min_scene = model.min + model.pos

                    #TODO:Add some test for checking if object is inside of printing space of printer
                    if not model.intersection_model_list_model_(scene_tmp):
                        return

                position_vector[0] += model.boundingSphereSize*.1
                position_vector[1] += model.boundingSphereSize*.1

    def get_whole_scene_in_one_mesh(self, gcode_generate=False):
        return Mesh(np.concatenate([i.get_mesh(True, gcode_generate).data for i in self.models if i.isVisible]))

    def save_whole_scene_to_one_stl_file(self, filename):
        whole_scene = self.get_whole_scene_in_one_mesh(True)
        whole_scene.save(filename)

    def is_scene_printable(self):
        scene_models = [m for m in self.models if m.isVisible]
        if len(scene_models) == 0:
            return False
        for model in scene_models:
            if not model.is_in_printing_space(self.controller.printing_parameters.get_printer_parameters(self.controller.actual_printer)):
                return False
        return True




class Model(object):
    '''
    this is reprezentation of model data
    '''
    newid = itertools.count().next
    def __init__(self):
        #IDs
        self.id = Model.newid()+1

        self.isVisible = True
        self.is_in_printing_area = True

        self.colorId = [(self.id & 0x000000FF) >> 0, (self.id & 0x0000FF00) >> 8, (self.id & 0x00FF0000) >> 16]
        self.select_color = [255, 75, 0, 255]
        self.color = [235, 235, 235, 255]

        self.z_cursor = 0.0

        self.face_colors = []
        self.normal_groups = {}

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

        self.t0 = []
        self.t1 = []
        self.t2 = []

        self.n0 = []
        self.n1 = []
        self.n2 = []

        self.rotationAxis = []
        self.scaleAxis = []

        self.dataTmp = []

        self.normal = []
        self.displayList = []

        self.mesh = None
        self.temp_mesh = None
        self.vao = None

        self.texture_size = 16
        self.variable_texture_data = np.full((self.texture_size*self.texture_size*4), 255, dtype=np.int)
        self.variable_layer_height_data = np.zeros((11), dtype=np.float32)

        self.variable_texture = []


        #transformation data, connected to scene
        self.pos = np.array([.0, .0, .0])
        self.pos_old = np.array([.0, .0, .0])
        self.rot = np.array([.0, .0, .0])
        self.rot_scene = np.array([.0, .0, .0])
        self.scale = np.array([1., 1., 1.])
        self.old_scale = np.array([1., 1., 1.])
        self.scaleDefault = [.1, .1, .1]

        self.min_scene = [.0, .0, .0]
        self.max_scene = [.0, .0, .0]

        #history state
        self.pos_hist = np.array([.0, .0, .0])
        self.rot_hist = np.array([.0, .0, .0])
        self.scale_hist = np.array([1., 1., 1.])
        #history state

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
        self.max_bs = np.array([0.])
        self.size = np.array([.0, .0, .0])
        self.size_origin = np.array([.0, .0, .0])

        #status of object
        self.is_changed = True

        #source file data
        #example car.stl
        self.filename = ""
        self.normalization_flag = False

        #self.recalculate_texture()


    def __deepcopy__(self, memodict={}):
        m = Model()

        m.filename = deepcopy(self.filename)
        m.mesh = deepcopy(self.mesh)
        m.normal = deepcopy(self.normal)

        m.pos = deepcopy(self.pos)
        m.scale = deepcopy(self.scale)
        m.rot = deepcopy(self.rot)

        m.tiled_normals = deepcopy(self.tiled_normals)
        m.parent = self.parent

        m.min = deepcopy(self.min)
        m.max = deepcopy(self.max)

        m.v0 = deepcopy(self.v0)
        m.v1 = deepcopy(self.v1)
        m.v2 = deepcopy(self.v2)

        m.t0 = deepcopy(self.v0)
        m.t1 = deepcopy(self.t1)
        m.t2 = deepcopy(self.t2)

        m.n0 = deepcopy(self.n0)
        m.n1 = deepcopy(self.n1)
        m.n2 = deepcopy(self.n2)


        m.min_scene = deepcopy(self.min_scene)
        m.max_scene = deepcopy(self.max_scene)

        m.size = deepcopy(self.size)
        m.size_origin = deepcopy(self.size_origin)

        m.boundingSphereSize = deepcopy(self.boundingSphereSize)
        m.boundingSphereCenter = deepcopy(self.boundingSphereCenter)
        m.boundingBox = deepcopy(self.boundingBox)
        m.boundingMinimalPoint = deepcopy(self.boundingMinimalPoint)
        m.zeroPoint = deepcopy(self.zeroPoint)

        m.temp_mesh = deepcopy(self.mesh)
        return m



    def recalculate_texture(self):
        #TODO:
        #coef = (self.texture_size*self.texture_size)/11.
        #coef = [int(np.floor(((self.texture_size * self.texture_size*4.) / 11.) * i)) for i in xrange(0, 11)]
        #interpolate = [i for i in xrange(0, self.texture_size * self.texture_size)]
        #self.variable_layer_height_data
        #print("Coef: " + str(coef))

        print("variable vector: " + str(len(self.variable_layer_height_data)))
        pprint(self.variable_layer_height_data)

        interpolated_vector = np.array([])
        for i in xrange(0, 10, 1):
            interpolated_vector = np.append(interpolated_vector,
                np.linspace(self.variable_layer_height_data[i],
                            self.variable_layer_height_data[i+1],
                            np.floor(self.texture_size*self.texture_size)/11.)
                )

        print("Interpolated vector: " + str(len(interpolated_vector)))
        pprint(interpolated_vector)


        '''
        n = 0
        for i in xrange(0, self.texture_size*self.texture_size*4, 4):
            change = 0.0
            if i in coef:
                print(i)
                change = self.variable_layer_height_data[n]
                n+=1

            self.variable_texture_data[i + 0] = 100 + int(change*75) # R
            self.variable_texture_data[i + 1] = 100 + int(change*75) # G
            self.variable_texture_data[i + 2] = 100 + int(change*75) # B
            self.variable_texture_data[i + 3] = 255 # A
        '''

        #self.variable_texture_data = np.array([], dtype=np.int)


        for n in xrange(0, self.texture_size*self.texture_size, 1):
            if n in interpolated_vector:
                i = interpolated_vector[n*-1]
            else:
                i = 0.0
            if i == 0.0:
                self.variable_texture_data[n * 4 + 0] = 255
                self.variable_texture_data[n * 4 + 1] = 255
                self.variable_texture_data[n * 4 + 2] = 255
                self.variable_texture_data[n * 4 + 3] = 255
                #np.append(self.variable_texture_data, np.array([255, 255, 255, 255], dtype=np.int))
            elif i < 0.0:
                self.variable_texture_data[n * 4 + 0] = 1
                self.variable_texture_data[n * 4 + 1] = 1
                self.variable_texture_data[n * 4 + 2] = int(100*-i)
                self.variable_texture_data[n * 4 + 3] = 255
                #np.append(self.variable_texture_data, np.array([55, 55, int(100*i), 255], dtype=np.int))
            elif i > 0.0:
                self.variable_texture_data[n * 4 + 0] = int(100*i)
                self.variable_texture_data[n * 4 + 1] = 1
                self.variable_texture_data[n * 4 + 2] = 1
                self.variable_texture_data[n * 4 + 3] = 255
                #np.append(self.variable_texture_data, np.array([int(100*i), 55, 55, 255], dtype=np.int))

        #print("Data: " + str(self.variable_texture_data))


        self.variable_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.variable_texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.texture_size, self.texture_size, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.variable_texture_data)
        glBindTexture(GL_TEXTURE_2D, 0)


    def reset_transformation(self):
        self.scale[0] = 1.
        self.scale[1] = 1.
        self.scale[2] = 1.

        self.rot[0] = 0.
        self.rot[1] = 0.
        self.rot[2] = 0.

        self.pos[0] = 0.
        self.pos[1] = 0.

        self.update_min_max()
        self.place_on_zero()




    def calculate_normal_groups(self):
        actual_id = 0
        id=0

        #d = defaultdict(int)

        self.mesh.normals = np.array([n for n in self.mesh.normals])

        Vect = namedtuple("Vect", ["x", "y", "z"])
        d = {}


        for normal in self.mesh.normals:
            if Vect(self.str_c(normal[0]), self.str_c(normal[1]), self.str_c(normal[2])) in d:
                id = d[Vect(self.str_c(normal[0]), self.str_c(normal[1]), self.str_c(normal[2]))]
            else:
                d[Vect(self.str_c(normal[0]), self.str_c(normal[1]), self.str_c(normal[2]))] = actual_id
                actual_id += 1


        self.face_colors = [[[(d[Vect(self.str_c(i[0]), self.str_c(i[1]), self.str_c(i[2]))] & 0x000000FF) >> 0,
                                       (d[Vect(self.str_c(i[0]), self.str_c(i[1]), self.str_c(i[2]))] & 0x0000FF00) >> 8,
                                       (d[Vect(self.str_c(i[0]), self.str_c(i[1]), self.str_c(i[2]))] & 0x00FF0000) >> 16],
                                      [(d[Vect(self.str_c(i[0]), self.str_c(i[1]), self.str_c(i[2]))] & 0x000000FF) >> 0,
                                       (d[Vect(self.str_c(i[0]), self.str_c(i[1]), self.str_c(i[2]))] & 0x0000FF00) >> 8,
                                       (d[Vect(self.str_c(i[0]), self.str_c(i[1]), self.str_c(i[2]))] & 0x00FF0000) >> 16],
                                      [(d[Vect(self.str_c(i[0]), self.str_c(i[1]), self.str_c(i[2]))] & 0x000000FF) >> 0,
                                       (d[Vect(self.str_c(i[0]), self.str_c(i[1]), self.str_c(i[2]))] & 0x0000FF00) >> 8,
                                       (d[Vect(self.str_c(i[0]), self.str_c(i[1]), self.str_c(i[2]))] & 0x00FF0000) >> 16]] for i in self.mesh.normals]

        '''
        for normal in self.mesh.normals:
            if str(normal) in self.normal_groups:
                id = self.normal_groups[str(normal)]
            else:
                self.normal_groups[str(normal)] = actual_id
                actual_id+=1



        self.face_colors = np.array([[[(self.normal_groups[str(i)] & 0x000000FF) >> 0,
                              (self.normal_groups[str(i)] & 0x0000FF00) >> 8,
                              (self.normal_groups[str(i)] & 0x00FF0000) >> 16],
                             [(self.normal_groups[str(i)] & 0x000000FF) >> 0,
                              (self.normal_groups[str(i)] & 0x0000FF00) >> 8,
                              (self.normal_groups[str(i)] & 0x00FF0000) >> 16],
                             [(self.normal_groups[str(i)] & 0x000000FF) >> 0,
                              (self.normal_groups[str(i)] & 0x0000FF00) >> 8,
                              (self.normal_groups[str(i)] & 0x00FF0000) >> 16]] for i in self.mesh.normals])
        '''



        #print("Face colors:")
        #pprint(self.face_colors)

    def str_c(self, input):
        if input == 0.0:
            input = 0.0
        return str(input)

    def clear_state(self):
        self.is_changed = False

    def changing(self):
        self.is_changed = True

    def is_in_printing_space(self, printer):
        min = self.min_scene
        max = self.max_scene

        if max[0] <= (printer['printing_space'][0]*.05) and min[0] >= (printer['printing_space'][0]*-.05):
                if max[1] <= (printer['printing_space'][1]*.05) and min[1] >= (printer['printing_space'][1]*-.05):
                    if max[2] <= printer['printing_space'][2]*0.1 and min[2] >= -0.1:
                        #print("Max[2] " + str(max[2]))
                        #print("Printing space[2] " + str(printer['printing_space'][2]))
                        self.is_in_printing_area = True
                        return True
                    else:
                        print("naruseni v Z")
                        self.is_in_printing_area = False
                        return False
                else:
                    #print("naruseni v Y")
                    self.is_in_printing_area = False
                    return False
        else:
            #print("naruseni v X")
            self.is_in_printing_area = False
            return False

    #@timing
    def get_mesh(self, transform=True, generate_gcode=False, default_scale=True):
        data = np.zeros(len(self.mesh.vectors), dtype=Mesh.dtype)

        vectors = self.mesh.vectors.copy()

        rx_matrix = Mesh.rotation_matrix([1.0, 0.0, 0.0], self.rot[0])
        ry_matrix = Mesh.rotation_matrix([0.0, 1.0, 0.0], self.rot[1])
        rz_matrix = Mesh.rotation_matrix([0.0, 0.0, 1.0], self.rot[2])

        rotation_matrix = np.dot(np.dot(rx_matrix, ry_matrix), rz_matrix)

        scale_matrix = np.array([[1., 0., 0.],
                                 [0., 1., 0.],
                                 [0., 0., 1.]]) * self.scale


        final_rotation = rotation_matrix
        final_scale = scale_matrix
        #final_matrix = np.dot(final_rotation, final_scale)
        final_matrix = np.dot(final_scale, final_rotation)


        if transform and generate_gcode:
            for i in range(3):
                vectors[:, i] = vectors[:, i].dot(final_matrix)

            printer = self.parent.controller.printing_parameters.get_printer_parameters(self.parent.controller.actual_printer)
            #print("Printer: " + str(printer))
            vectors += self.pos + (np.array([printer['printing_space'][0]*0.5*.1,
                                             printer['printing_space'][1]*0.5*.1,
                                             printer['printing_space'][2]*0.5*.1]))
        elif transform and not generate_gcode:
            vectors += self.pos

        if default_scale:
            vectors /= np.array(self.scaleDefault)

        data['vectors'] = vectors

        return Mesh(data)

    def normalize_object(self):
        #vektor od nuly po boundingSphereCenter, tedy rozdil ktery je potreba pricist ke vsem souradnicim
        r = np.array([.0, .0, .0]) - np.array(self.boundingSphereCenter)

        self.mesh.vectors = self.mesh.vectors + r

        self.mesh.update_min()
        self.mesh.update_max()
        self.min = self.mesh.min_
        self.max = self.mesh.max_

        self.boundingSphereCenter = np.array(self.boundingSphereCenter) + r

        self.zeroPoint = np.array(self.zeroPoint) + r
        self.zeroPoint[2] = self.min[2]

        self.pos = np.array([.0, .0, .0]) - self.zeroPoint
        self.zeroPoint[2] = 0.

        self.normalization_flag = True

    def set_move(self, vector, add=True, place_on_zero=False):
        vector = np.array(vector)
        if add:
            self.pos += vector
        else:
            self.pos = vector
        #self.parent.controller.show_message_on_status_bar("Place on %s %s" % ('{:.2}'.format(self.pos[0]), '{:.2}'.format(self.pos[1])))
        self.min_scene = self.min + self.pos
        self.max_scene = self.max + self.pos

        if place_on_zero:
            self.place_on_zero()

    def make_normals(self):
        self.tiled_normals = np.tile(self.mesh.normals, 3)

    def apply_rotation(self):
        self.rotation_matrix = np.dot(self.rotation_matrix, self.temp_rotation)
        self.temp_rotation = np.array([[ 1.,  0.,  0.],
                                        [ 0.,  1.,  0.],
                                        [ 0.,  0.,  1.]])

    '''
    def apply_all_transformation(self):
        rx_matrix = Mesh.rotation_matrix([1.0, 0.0, 0.0], self.rot[0])
        ry_matrix = Mesh.rotation_matrix([0.0, 1.0, 0.0], self.rot[1])
        rz_matrix = Mesh.rotation_matrix([0.0, 0.0, 1.0], self.rot[2])

        rotation_matrix = np.dot(np.dot(rx_matrix, ry_matrix), rz_matrix)

        scale_matrix = np.array([[1., 0., 0.],
                                 [0., 1., 0.],
                                 [0., 0., 1.]]) * self.scale

        final_rotation = rotation_matrix
        final_scale = scale_matrix
        final_matrix = np.dot(final_rotation, final_scale)

        for i in range(3):
            self.temp_mesh.vectors[:, i] = self.mesh.vectors[:, i].dot(final_matrix)

        self.temp_mesh.normals = self.mesh.normals.dot(final_rotation)
        self.make_normals()

        self.temp_mesh.update_min()
        self.temp_mesh.update_max()

        self.min = self.temp_mesh.min_
        self.max = self.temp_mesh.max_
        self.min_scene = self.min + self.pos
        self.max_scene = self.max + self.pos

        #self.place_on_zero()

        self.is_changed = False
    '''

    '''
    def start_edit(self):
        self.rot_hist = deepcopy(self.rot)
        self.scale_hist = deepcopy(self.scale)
        self.pos_hist = deepcopy(self.pos)
        self.is_changed = True

    def apply_changes(self):
        #print("Apply changes")
        self.pos_hist = np.array([.0, .0, .0])
        self.rot_hist = np.array([.0, .0, .0])
        self.scale_hist = np.array([1., 1., 1.])

        self.update_min_max()

        self.is_changed = False

    def discard_changes(self):
        #print("Discard changes")
        self.pos = deepcopy(self.pos_hist)
        self.scale = deepcopy(self.scale_hist)
        self.rot = deepcopy(self.rot_hist)
        #self.apply_all_transformation()
        self.is_changed = False

    '''

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


    @timing
    def set_rot(self, x, y, z, add=False, update_min_max=True, place_on_zero=True):
        '''
        if x > (2*np.pi):
            x = divmod(x,2*np.pi)
        if y > (2*np.pi):
            y = divmod(y,2*np.pi)
        if z > (2*np.pi):
            z = divmod(z,2*np.pi)
        '''
        #print("uhel v set_rot: " + str(z))

        if add:
            self.rot[0] += x
            self.rot[1] += y
            self.rot[2] += z
        else:
            self.rot[0] = x
            self.rot[1] = y
            self.rot[2] = z


        if update_min_max:
            self.update_min_max()
        if place_on_zero:
            self.place_on_zero()

    def set_scale_abs(self, x, y, z):
        #printer = self.parent.controller.printing_parameters.get_printer_parameters(self.parent.controller.actual_printer)
        #if (x * self.size_origin[0] > .5) and (y * self.size_origin[1] > .5) and (z * self.size_origin[2] > .5)\
        #    and (x * self.size_origin[0] < printer['printing_space'][0]*.1) and\
        #        (y * self.size_origin[1] < printer['printing_space'][1]*.1) and\
        #        (z * self.size_origin[2] < printer['printing_space'][2]*.1):

        self.old_scale = deepcopy(self.scale)

        self.scale[0] = x
        self.scale[1] = y
        self.scale[2] = z

        #self.update_min_max()
        self.update_min_max_quick_change_of_scale()
        self.place_on_zero()

    def set_scale_coef(self, coef):
        self.old_scale = deepcopy(self.scale)

        self.scale *= coef

        # self.update_min_max()
        self.update_min_max_quick_change_of_scale()
        self.place_on_zero()



    def update_position(self):
        self.update_min_max()
        if self.min[2] < 0.:
            len = self.min[2] * -1.0
            self.pos[2]+=len
            self.update_min_max()

    @timing
    def update_min_max(self):
        #self.temp_mesh = deepcopy(self.mesh)

        rx_matrix = Mesh.rotation_matrix([1.0, 0.0, 0.0], self.rot[0])
        ry_matrix = Mesh.rotation_matrix([0.0, 1.0, 0.0], self.rot[1])
        rz_matrix = Mesh.rotation_matrix([0.0, 0.0, 1.0], self.rot[2])

        rotation_matrix = np.dot(np.dot(rx_matrix, ry_matrix), rz_matrix)

        scale_matrix = np.array([[1., 0., 0.],
                                 [0., 1., 0.],
                                 [0., 0., 1.]]) * self.scale

        final_rotation = rotation_matrix
        final_scale = scale_matrix
        #final_matrix = np.dot(final_rotation, final_scale)
        final_matrix = np.dot(final_scale, final_rotation)

        for i in range(3):
            self.temp_mesh.vectors[:, i] = self.mesh.vectors[:, i].dot(final_matrix)

        #self.temp_mesh.normals = self.mesh.normals.dot(final_rotation)

        self.temp_mesh.update_min()
        self.temp_mesh.update_max()
        self.min = self.temp_mesh.min_
        self.max = self.temp_mesh.max_

        self.size = self.max - self.min

        self.min_scene = self.min + self.pos
        self.max_scene = self.max + self.pos


    def update_min_max_quick_change_of_scale(self):
        diff_scale = np.array([self.scale[0] / self.old_scale[0],
                                self.scale[1] / self.old_scale[1],
                                self.scale[2] / self.old_scale[2]])

        self.max *= diff_scale
        self.min *= diff_scale

        self.size = self.max - self.min

        self.min_scene = self.min + self.pos
        self.max_scene = self.max + self.pos





    def recalc_bounding_sphere(self):
        max_l = np.linalg.norm(self.max)
        min_l = np.linalg.norm(self.min)
        if max_l > min_l:
            self.boundingSphereSize = max_l
        else:
            self.boundingSphereSize = min_l

    def put_array_to_gl(self):
        glNormalPointerf(self.tiled_normals)
        #print("Data normals:")
        #pprint(self.face_colors)
        #print("Data vectors:")
        #pprint(self.mesh.vectors)
        #glColorPointerf(self.face_colors)
        glVertexPointerf(self.mesh.vectors)

        #glNormalPointerf(np.tile(self.draw_mesh['normals'], 3))
        #glVertexPointerf(self.draw_mesh['vectors'])

    def render(self, picking=False, blending=False):
        is_in_printing_space = True

        if not self.isVisible:
            return
        glPushMatrix()

        if self.parent.controller.settings['debug']:
            glPointSize(5.0)
            glColor3f(1., .0, .0)
            glBegin(GL_POINTS)
            glVertex3f(self.min_scene[0], self.min_scene[1], self.min_scene[2])
            glVertex3f(self.max_scene[0], self.min_scene[1], self.min_scene[2])
            glVertex3f(self.min_scene[0], self.max_scene[1], self.min_scene[2])
            glVertex3f(self.min_scene[0], self.min_scene[1], self.max_scene[2])
            glVertex3f(self.max_scene[0], self.min_scene[1], self.max_scene[2])
            glVertex3f(self.max_scene[0], self.max_scene[1], self.min_scene[2])
            glVertex3f(self.min_scene[0], self.max_scene[1], self.max_scene[2])
            glVertex3f(self.max_scene[0], self.max_scene[1], self.max_scene[2])
            glEnd()

            glColor3f(.0, .0, 1.)
            glBegin(GL_POINTS)
            glVertex3f(self.zeroPoint[0], self.zeroPoint[1], self.zeroPoint[2])
            glEnd()

        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        rx_matrix = Mesh.rotation_matrix([1.0, 0.0, 0.0], self.rot[0])
        ry_matrix = Mesh.rotation_matrix([0.0, 1.0, 0.0], self.rot[1])
        rz_matrix = Mesh.rotation_matrix([0.0, 0.0, 1.0], self.rot[2])

        rotation_matrix = np.dot(np.dot(rx_matrix, ry_matrix), rz_matrix)

        scale_matrix = np.array([[ 1.,  0.,  0.],
                                        [ 0.,  1.,  0.],
                                        [ 0.,  0.,  1.]]) * self.scale

        final_rotation = rotation_matrix
        final_scale = scale_matrix
        #final_matrix = np.dot(final_rotation, final_scale)
        final_matrix = np.dot(final_scale, final_rotation)

        glMultMatrixf(self.matrix3_to_matrix4(final_matrix))

        #m = np.array([1.,0.,0.,0.,
        #          0.,1.,0.,0.,
        #          0.,0.,1.,0.,
        #          0.,0.,0.,1.0])
        #glGetFloatv(GL_MODELVIEW_MATRIX, m)
        #print(str(m))



        self.put_array_to_gl()

        glEnableClientState(GL_VERTEX_ARRAY)
        #if not picking:
        #    glEnableClientState(GL_COLOR_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        if picking:
            glDisable(GL_BLEND)
            glDisable(GL_LIGHTING)
        elif blending:
            #glCullFace(GL_BACK)
            #glEnable(GL_CULL_FACE)
            glEnable(GL_LIGHTING)
            #glDisable(GL_DEPTH_TEST)
            #glEnable(GL_BLEND)
        else:
            glDisable(GL_BLEND)
            glEnable(GL_LIGHTING)
            glEnable(GL_DEPTH_TEST)

        if picking:
            glColor3ubv(self.colorId)
        else:
            if blending:
                glColor4ub(175, 175, 175, 150)
                #glColor4f(.4, .4, .4, .75)
            else:
                if self.is_in_printing_space(self.parent.controller.printing_parameters.get_printer_parameters(self.parent.controller.actual_printer)):
                    if self.selected:
                        glColor4ubv(self.select_color)
                    else:
                        glColor4ubv(self.color)
                else:
                    glColor4f(0.25, 0.25, 0.25, 1.)


        glDrawArrays(GL_TRIANGLES, 0, len(self.mesh.vectors) * 3)


        glDisableClientState(GL_VERTEX_ARRAY)
        #if not picking:
        #    glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)

        if self.is_in_printing_area == False:
            font = self.parent.controller.view.font
            font.setPointSize(35)
            glDisable(GL_LIGHTING)
            glDisable(GL_DEPTH_TEST)
            glColor3ub(255, 97, 0)
            self.parent.controller.view.glWidget.renderText(0., 0., 0., u"!", font)
        if blending:
            glCullFace(GL_BACK)
            glDisable(GL_CULL_FACE)
            glDisable(GL_BLEND)
            glEnable(GL_LIGHTING)
            glEnable(GL_DEPTH_TEST)
        else:
            #glDisable(GL_CULL_FACE)
            #glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_FALSE)
            #glCullFace(GL_FRONT)
            glDisable(GL_BLEND)
            glEnable(GL_LIGHTING)
            glEnable(GL_DEPTH_TEST)

        glPopMatrix()



    def matrix3_to_matrix4(self, matrix3):
        mat = [i+[0.] for i in matrix3.tolist()]
        mat += [[0.,0.,0.,1.]]
        return mat


    def make_display_list(self):
        #vert = [[ 1., 0., 0.], [ 0., 1., 0.], [ 1., 1., 0.]]
        #norm = [[ 0., 0., 1.], [ 0., 0., 1.], [ 0., 0., 1.]]


        genList = glGenLists(1)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        glNormalPointerf(np.tile(self.mesh.normals, 3))
        glVertexPointerf(self.mesh.vectors)

        #glNormalPointerf(norm)
        #glVertexPointerf(vert)


        glNewList(genList, GL_COMPILE)

        glDrawArrays(GL_TRIANGLES, 0, len(self.mesh.vectors)*3)

        glEndList()

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)

        return genList

    def intersection_model_model_by_BB(self, model):
        #intersection by collision of BB
        min = self.min_scene
        max = self.max_scene
        model_min = model.min_scene
        model_max = model.max_scene
        d = self.parent.model_position_offset
        #print("intersection model model: " + str(d))
        return not(max[0]+d<model_min[0] or model_max[0]<min[0]-d or max[1]+d<model_min[1] or model_max[1]<min[1]-d)

    def intersection_model_list_model_(self, list):
        for m in list:
            if m.isVisible:
                if self.intersection_model_model_by_BB(m):
                    return True
        return False

    @timing
    def intersectionRayModel(self, rayStart, rayEnd):
        ray = rayEnd - rayStart
        ray /= np.linalg.norm(ray)

        data = self.temp_mesh

        counter = 0
        for tri in data.vectors+self.pos:
            b = [.0, .0, .0]

            e1 = tri[1]
            e1 -= tri[0]
            e2 = tri[2]
            e2 -= tri[0]

            n = self.temp_mesh.normals[counter]

            q = np.cross(ray, e2)
            a = np.dot(e1, q)

            counter += 1
            if (np.dot(n, ray) >= .0) or (abs(a) <= .0001):
                continue

            s = np.array(rayStart)
            s -= tri[0]
            s /= a

            r = np.cross(s, e1)
            b[0] = np.dot(s, q)
            b[1] = np.dot(r, ray)
            b[2] = 1.0 - b[0] - b[1]

            if (b[0] < .0) or (b[1] < .0) or (b[2] < .0):
                continue

            t = np.dot(e2, r)
            if t >= .0:
                point = rayStart + t*ray
                return True, point
            else:
                continue
        return False, None

    @timing
    def intersectionRayModel2(self, rayStart, rayEnd):
        ray = rayEnd - rayStart
        ray /= np.linalg.norm(ray)

        # data = self.get_mesh(True, False, False)
        data = self.temp_mesh

        tri_0 = data.vectors[:, 0]
        tri_1 = data.vectors[:, 1]
        tri_2 = data.vectors[:, 2]

        e1 = tri_1
        e1 -= tri_0
        e2 = tri_2
        e2 -= tri_0

        n = data.normals

        q = np.cross(ray, e2)
        a = np.dot(e1, q)




        counter = 0
        for tri in data.vectors + self.pos:
            # for tri in np.nditer(data.vectors):

            # v0 = tri[0]# + self.pos
            # v1 = tri[1]# + self.pos
            # v2 = tri[2]# + self.pos

            b = [.0, .0, .0]
            # e1 = np.array(v1)
            # e1 -= v0
            # e2 = np.array(v2)
            # e2 -= v0

            e1 = tri[1]
            e1 -= tri[0]
            e2 = tri[2]
            e2 -= tri[0]

            n = self.temp_mesh.normals[counter]

            q = np.cross(ray, e2)
            a = np.dot(e1, q)

            counter += 1
            if (np.dot(n, ray) >= .0) or (abs(a) <= .0001):
                continue

            s = np.array(rayStart)
            s -= tri[0]
            s /= a

            r = np.cross(s, e1)
            b[0] = np.dot(s, q)
            b[1] = np.dot(r, ray)
            b[2] = 1.0 - b[0] - b[1]

            if (b[0] < .0) or (b[1] < .0) or (b[2] < .0):
                continue

            t = np.dot(e2, r)
            if t >= .0:
                point = rayStart + t * ray
                return tri, point
            else:
                continue
        return False

    @timing
    def intersectionRayModel3(self, rayStart, rayEnd):
        ray = rayEnd - rayStart
        ray /= np.linalg.norm(ray)

        n = self.temp_mesh.normals
        vectors = self.temp_mesh.vectors+self.pos

        #b = np.array([0., 0., 0.])

        # print(tri_1)

        tri_0 = vectors[:, 0]
        tri_1 = vectors[:, 1]
        tri_2 = vectors[:, 2]

        e1 = tri_1
        e1 -= tri_0
        e2 = tri_2
        e2 -= tri_0

        q = np.cross(ray, e2)
        # a = np.dot(e1, q)
        a = np.einsum('ij,ij->i', e1, q)
        shape_tri = tri_0.shape


        f1 = (np.dot(n, ray) >= .0) | (np.absolute(a) <= .0001)
        #print("F1:" + str(f1))
        if not f1.any():
            print("Nic v F1")
            return False, None

        s = np.tile(rayStart, shape_tri[0])
        s = s.reshape(shape_tri)
        s -= tri_0
        # s = np.divide(s, a[:, None])
        # s /= a[:, None]
        s = np.nan_to_num(s / a[:, None])

        r = np.nan_to_num(np.cross(s, e1))

        # b[0] = np.dot(s, q)
        b_0 = np.nan_to_num(np.einsum('ij,ij->i', s, q))
        # b[1] = np.dot(r, ray)
        # b_1 = np.einsum('ij,ij->i', r, ray)
        b_1 = np.nan_to_num(np.dot(r, ray))
        # b[2] = 1.0 - b[0] - b[1]
        b_2 = np.nan_to_num(1.0 - b_0 - b_1)

        f2 = (b_0 < .0) | (b_1 < .0) | (b_2 < .0)
        #print("F2:" + str(f2))
        if not np.logical_xor(f1, f2).any():
            print("Nic v F2")
            return False, None

        # t = np.dot(e2, r)
        t = np.nan_to_num(np.einsum('ij,ij->i', e2, r))
        f3 = (t >= 0.)
        f_final = np.logical_xor(f1, f2, f3)
        if not f_final.any():
            print("Nic v F3")
            return False, None
        else:
            #t_fin = np.min(t[f_final])
            t_fin = t[f_final][0]*.001
            point = rayStart + t_fin * ray
            return True, point



    #TODO:Better!!!
    def place_on_face(self, ray_start, ray_end):
        value = self.intersectionRayModel(np.array(ray_start), np.array(ray_end))
        if type(value) == bool:
            return []
        else:
            hit_face, normal = value

        up_vector = np.array([0., 0., -1.])

        #calc alpha
        #rotation around X vector
        normal_face_vector_tmp1 = deepcopy(normal)
        normal_face_vector_tmp1[0] = 0.
        alpha = AppScene.calc_angle(up_vector, normal_face_vector_tmp1)

        #calc beta
        #rotation around Y vector
        normal_face_vector_tmp2 = deepcopy(normal)
        normal_face_vector_tmp2[1] = 0.
        beta = AppScene.calc_angle(up_vector, normal_face_vector_tmp2)


        print("Nalezeny uhly alpha %s a beta %s" % (str(alpha), str(beta)))
        if alpha<=beta:
            print("Alpha")
            self.set_rot(np.deg2rad(alpha), 0., 0.)
        else:
            print("Beta")
            self.set_rot(0., np.deg2rad(beta), 0.)
        return deepcopy(hit_face)


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

class ModelTypeObj(ModelTypeAbstract):


    @staticmethod
    def load(filename):
        logging.debug("this is OBJ file reader")
        swapyz = False
        vertices = []
        normals = []
        texcoords_array = []
        faces = []

        for line in open(filename, "r"):
            if line.startswith('#'): continue
            values = line.split()
            if not values: continue
            if values[0] == 'v':
                v = map(float, values[1:4])
                if swapyz:
                    v = v[0], v[2], v[1]
                vertices.append(v)
            elif values[0] == 'vn':
                v = map(float, values[1:4])
                if swapyz:
                    v = v[0], v[2], v[1]
                normals.append(v)
            elif values[0] == 'vt':
                texcoords_array.append(map(float, values[1:3]))
            #elif values[0] in ('usemtl', 'usemat'):
            #    material = values[1]
            #elif values[0] == 'mtllib':
            #    mtl = MTL(values[1])
            elif values[0] == 'f':
                face = []
                texcoords = []
                norms = []
                for v in values[1:]:
                    w = v.split('/')
                    face.append(int(w[0]))
                    if len(w) >= 2 and len(w[1]) > 0:
                        texcoords.append(int(w[1]))
                    else:
                        texcoords.append(0)
                    if len(w) >= 3 and len(w[2]) > 0:
                        norms.append(int(w[2]))
                    else:
                        norms.append(0)
                faces.append((face, norms, texcoords))

        model = Model()

        if filename:
            model.filename = basename(filename)
        else:
            model.filename = ""


        #print("Vertices N: " + str(len(vertices)))
        #print("Texcoords N: " + str(len(texcoords_array)))
        #print("Normals N: " + str(len(normals)))
        #print("Faces N: " + str(len(faces)))


        for face in faces:
            vert, norm, texcoord = face
            #print("Vertex indexes: " + str(vert))
            #print("Texcoord indexes: " + str(texcoord))
            model.v0.append(vertices[vert[0] - 1])
            model.n0.append(normals[norm[0] - 1])
            model.t0.append(texcoords_array[texcoord[0] - 1])

            model.v1.append(vertices[vert[1] - 1])
            model.n1.append(normals[norm[1] - 1])
            model.t1.append(texcoords_array[texcoord[1] - 1])

            model.v2.append(vertices[vert[2] - 1])
            model.n2.append(normals[norm[2] - 1])
            model.t2.append(texcoords_array[texcoord[2] - 1])


        return model


class ModelTypeStl(ModelTypeAbstract):
    '''
    Concrete ModelType class for STL type file, it can load binary and char file
    '''

    @staticmethod
    def load(filename):
        #logging.debug("this is STL file reader")
        #print(filename)
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

        #print(str(model.zeroPoint))

        model.mesh = mesh

        #normalize position of object on 0
        if normalize:
            model.normalize_object()

        model.max_bs = np.max(np.linalg.norm(model.mesh.vectors, axis=2))

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

        model.temp_mesh = deepcopy(model.mesh)
        model.make_normals()
        model.isVisible = True

        #model.calculate_normal_groups()

        #model.face_colors = np.array([[np.absolute(i), np.absolute(i), np.absolute(i)] for i in mesh.normals])


        #model.displayList = model.make_display_list()
        #model.make_vao()

        gc.collect()

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
