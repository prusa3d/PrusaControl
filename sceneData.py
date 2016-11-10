# -*- coding: utf-8 -*-
import logging
from collections import defaultdict

import numpy as np
from abc import ABCMeta, abstractmethod
from os.path import basename

import time
from PyQt4.QtCore import QObject
from PyQt4.QtOpenGL import QGLBuffer
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
        self.copied_models = []
        self.printable = True
        self.camera_vector = np.array([0.,0.,0.])

        self.transformation_list = []
        self.actual_list_position = 0

        self.analyze_result_data_tmp = []

    def clear_history(self):
        self.transformation_list = []
        self.actual_list_position = 0

    def save_change(self, old_instance):
        if self.actual_list_position < len(self.transformation_list)-1:
            self.transformation_list = self.transformation_list[:self.actual_list_position+1]

        self.transformation_list.append([old_instance, deepcopy(old_instance.isVisible), np.copy(old_instance.scale), np.copy(old_instance.rot), np.copy(old_instance.pos)])
        self.actual_list_position = len(self.transformation_list)-1
        #self.controller.show_message_on_status_bar("Set state %s from %s" % ('{:2}'.format(self.actual_list_position), '{:2}'.format(len(self.transformation_list))))

    def make_undo(self):
        #just move pointer of transformation to -1 or leave on 0
        if self.actual_list_position >= 1:
            self.actual_list_position -= 1
            old_instance, isVisible, scale, rot, pos = self.transformation_list[self.actual_list_position]
            old_instance.isVisible = deepcopy(isVisible)
            old_instance.scale = np.copy(scale)
            old_instance.rot = np.copy(rot)
            old_instance.pos = np.copy(pos)
            old_instance.is_changed = True
            old_instance.update_min_max()
            #self.controller.show_message_on_status_bar("Set state %s from %s" % ('{:2}'.format(self.actual_list_position), '{:2}'.format(len(self.transformation_list))))

    def make_do(self):
        #move pointer of transformation to +1 or leave on last
        if self.actual_list_position < len(self.transformation_list)-1:
            self.actual_list_position += 1
            old_instance, isVisible, scale, rot, pos = self.transformation_list[self.actual_list_position]
            old_instance.isVisible = deepcopy(isVisible)
            old_instance.scale = np.copy(scale)
            old_instance.rot = np.copy(rot)
            old_instance.pos = np.copy(pos)
            old_instance.is_changed = True
            old_instance.update_min_max()
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
        normal /= np.linalg.norm(normal)
        vector /= np.linalg.norm(vector)
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
        self.copied_models = []
        for m in self.models:
            if m.selected and m.isVisible:
                self.copied_models.append(m)

    def paste_selected_objects(self):
        for i in self.copied_models:
            self.models.append(deepcopy(i))

        #self.automatic_models_position()



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

class Model(object):
    '''
    this is reprezentation of model data
    '''
    newid = itertools.count().next
    def __init__(self):
        #IDs
        self.id = Model.newid()+1

        self.isVisible = True

        self.colorId = [(self.id & 0x000000FF) >> 0, (self.id & 0x0000FF00) >> 8, (self.id & 0x00FF0000) >> 16]
        self.select_color = [255, 97, 0]
        self.color = [224, 224, 224]

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

        self.rotationAxis = []
        self.scaleAxis = []

        self.dataTmp = []

        self.normal = []
        self.displayList = []

        self.mesh = None
        self.temp_mesh = None
        self.vao = None


        #transformation data, connected to scene
        self.pos = np.array([.0, .0, .0])
        self.pos_old = np.array([.0, .0, .0])
        self.rot = np.array([.0, .0, .0])
        self.rot_scene = np.array([.0, .0, .0])
        self.scale = np.array([1., 1., 1.])
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
        self.size = np.array([.0, .0, .0])
        self.size_origin = np.array([.0, .0, .0])

        #self.color = [75./255., 119./255., 190./255.]
        #self.color = [34./255., 167./255., 240./255.]

        #status of object
        self.is_changed = True

        #source file data
        #example car.stl
        self.filename = ""
        self.normalization_flag = False

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

        m.min_scene = deepcopy(self.min_scene)
        m.max_scene = deepcopy(self.max_scene)

        m.size = deepcopy(self.size)
        m.size_origin = deepcopy(self.size_origin)

        m.temp_mesh = deepcopy(self.mesh)
        #print("Udelana kopie")
        return m


    def calculate_normal_groups(self):
        actual_id = 0
        id=0

        d = defaultdict(int)

        for normal in self.mesh.normals:
            if str(normal) in d:
                id = d[str(normal)]
            else:
                d[str(normal)] = actual_id
                actual_id += 1

        '''
        self.face_colors = [[[(d[str(i)] & 0x000000FF) >> 0,
                                       (d[str(i)] & 0x0000FF00) >> 8,
                                       (d[str(i)] & 0x00FF0000) >> 16],
                                      [(d[str(i)] & 0x000000FF) >> 0,
                                       (d[str(i)] & 0x0000FF00) >> 8,
                                       (d[str(i)] & 0x00FF0000) >> 16],
                                      [(d[str(i)] & 0x000000FF) >> 0,
                                       (d[str(i)] & 0x0000FF00) >> 8,
                                       (d[str(i)] & 0x00FF0000) >> 16]] for i in self.mesh.normals]
        '''

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





    def clear_state(self):
        self.is_changed = False

    def changing(self):
        self.is_changed = True

    def is_in_printing_space(self, printer):
        min = self.min_scene
        max = self.max_scene

        if max[0] <= (printer['printing_space'][0]*.05) and min[0] >= (printer['printing_space'][0]*-.05):
                if max[1] <= (printer['printing_space'][1]*.05) and min[1] >= (printer['printing_space'][1]*-.05):
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
        final_matrix = np.dot(final_rotation, final_scale)

        for i in range(3):
            vectors[:, i] = vectors[:, i].dot(final_matrix)



        if transform and generate_gcode:
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

    def set_rot(self, x, y, z, add=False, update_min_max=True, place_on_zero=True):
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
        printer = self.parent.controller.printing_parameters.get_printer_parameters(self.parent.controller.actual_printer)
        if (x * self.size_origin[0] > .5) and (y * self.size_origin[1] > .5) and (z * self.size_origin[2] > .5)\
            and (x * self.size_origin[0] < printer['printing_space'][0]*.1) and\
                (y * self.size_origin[1] < printer['printing_space'][1]*.1) and\
                (z * self.size_origin[2] < printer['printing_space'][2]*.1):
            self.scale[0] = x
            self.scale[1] = y
            self.scale[2] = z

            self.update_min_max()
            self.place_on_zero()


    def update_position(self):
        self.update_min_max()
        if self.min[2] < 0.:
            len = self.min[2] * -1.0
            self.pos[2]+=len
            self.update_min_max()

    @timing
    def update_min_max(self):
        self.temp_mesh = deepcopy(self.mesh)

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

        self.temp_mesh.update_min()
        self.temp_mesh.update_max()
        self.min = self.temp_mesh.min_
        self.max = self.temp_mesh.max_

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

        self.put_array_to_gl()

        glEnableClientState(GL_VERTEX_ARRAY)
        #glEnableClientState(GL_COLOR_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        if picking:
            glDisable(GL_LIGHTING)
        elif blending:
            glDisable(GL_LIGHTING)
            glDisable(GL_DEPTH_TEST)
        else:
            glEnable(GL_LIGHTING)
            glEnable(GL_DEPTH_TEST)

        if picking:
            glColor3ubv(self.colorId)
        else:
            if blending:
                glColor4ub(175, 175, 175, 175)
                #glColor4f(.4, .4, .4, .75)
            else:
                if self.is_in_printing_space(self.parent.controller.printing_parameters.get_printer_parameters(self.parent.controller.actual_printer)):
                    if self.selected:
                        glColor3ubv(self.select_color)
                    else:
                        glColor3ubv(self.color)
                else:
                    glColor3f(0.75, .0, .0)


        glDrawArrays(GL_TRIANGLES, 0, len(self.mesh.vectors) * 3)


        glDisableClientState(GL_VERTEX_ARRAY)
        #glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)

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


    def intersectionRayModel(self, rayStart, rayEnd):
        #self.dataTmp = itertools.izip(self.v0, self.v1, self.v2)
        #matrix = Matrix44.from_scale(Vector3(self.scale))
        #matrix = matrix * Matrix44.from_translation(Vector3(self.pos))
        #self.temp_mesh


        #w = deepcopy(rayEnd)
        #w -= rayStart
        #w.normalize()

        w = rayEnd - rayStart
        w /= np.linalg.norm(w)

        data = self.get_mesh(True, False, False)


        for i, tri in enumerate(data.vectors):
            v0 = tri[0]# + self.pos
            v1 = tri[1]# + self.pos
            v2 = tri[2]# + self.pos

            b = [.0, .0, .0]
            e1 = np.array(v1)
            e1 -= v0
            e2 = np.array(v2)
            e2 -= v0

            n = self.temp_mesh.normals[i]

            q = np.cross(w, e2)
            a = np.dot(e1, q)

            if (np.dot(n, w) >= .0) or (abs(a) <= .0001):
                continue

            s = np.array(rayStart)
            s -= v0
            s /= a

            r = np.cross(s, e1)
            b[0] = np.dot(s, q)
            b[1] = np.dot(r, w)
            b[2] = 1.0 - b[0] - b[1]

            if (b[0] < .0) or (b[1] < .0) or (b[2] < .0):
                continue

            t = np.dot(e2, r)
            if t >= .0:
                return tri, n
            else:
                continue
        return False



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


        #print("Nalezeny uhly alpha %s a beta %s" % (str(alpha), str(beta)))
        self.set_rot(np.deg2rad(alpha), 0., 0.)
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

        #print("Vertices: " + str(vertices))
        #print("Texcoords: " + str(texcoords_array))

        for face in faces:
            vert, norm, texcoord = face
            #print("Vertex indexes: " + str(vert))
            #print("Texcoord indexes: " + str(texcoord))
            model.v0.append(vertices[vert[0]-1])
            model.t0.append(texcoords_array[texcoord[0]-1])

            model.v1.append(vertices[vert[1]-1])
            model.t1.append(texcoords_array[texcoord[1]-1])

            model.v2.append(vertices[vert[2]-1])
            model.t2.append(texcoords_array[texcoord[2]-1])


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
