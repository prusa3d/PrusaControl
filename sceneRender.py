# -*- coding: utf-8 -*-
#import inspect
#import logging
from copy import deepcopy
from pprint import pprint

import OpenGL
import numpy as np

from sceneData import ModelTypeStl, ModelTypeObj

OpenGL.ERROR_CHECKING = False
OpenGL.ERROR_LOGGING = False

from OpenGL.GL import *
from OpenGL.GLU import *

import math

import numpy
import time

#from PyQt4.QtCore import QTimer
#from PyQt4.QtGui import QColor, QCursor
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtOpenGL import *
from PyQt4 import QtCore

from PIL.Image import *

import controller
#from camera import TargetedCamera
from glButton import GlButton

#Mesure
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print('%s function took %0.3f ms' % (f.func_name, (time2-time1)*1000.0))
        return ret
    return wrap


class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        #QGLWidget.__init__(self, parent)
        if hasattr(QGLFormat, 'setVersion'):
            f = QGLFormat()
            f.setVersion(2, 1)
            f.setDoubleBuffer(True)
            f.setSampleBuffers(True)
            f.setSamples(4)
            f.setSwapInterval(1)
            f.setProfile(QGLFormat.CoreProfile)
            c = QGLContext(f, None)
            QGLWidget.__init__(self, c, parent)
        else:
            QGLWidget.__init__(self, parent)

        self.setMouseTracking(True)

        self.parent = parent
        self.controller = self.parent.controller
        self.init_parametres()

        self.last_time = time.time()
        self.delta_t = 0.016
        self.last_fps = 100.
        self.fps_count = 0
        self.fps_time = 0.

        self.hitPoint = numpy.array([0.,0.,0.])
        self.oldHitPoint = numpy.array([0.,0.,0.])

        self.lightning_shader_program = QGLShaderProgram()
        self.variable_layer_shader_program = QGLShaderProgram()


        #properties definition
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.zoom = 0
        self.camera_position = numpy.array([0., 0. ,0.])

        self.lightning_shader_ok = False

        self.oldPos3d = [.0, .0, .0]

        #self.lightAmbient = [.0, .0, .0, .0]
        #self.lightDiffuse = [.0, .0, .0, .0]
        #self.lightPossition = [.0, .0, .0, .0]

        self.materialSpecular = [.0,.0,.0,.0]
        self.materialShiness = [.0]

        #DEBUG
        self.rayStart = numpy.array([0., 0. ,0.])
        self.rayDir = numpy.array([0., 0. ,0.])
        self.rayUp = numpy.array([0., 0. ,0.])
        self.rayRight = numpy.array([0., 0. ,0.])
        self.v0 = numpy.array([0., 0. ,0.])
        self.v1 = numpy.array([0., 0., 0.])
        self.v2 = numpy.array([0., 0., 0.])
        #DEBUG

        #screen properties
        self.w = 0
        self.h = 0

        self.init_parametres()

        self.sceneFrameBuffer = []
        self.image_background = []
        self.image_hotbed = []
        self.test_img = []

        #tools
        self.selectTool = None
        self.moveTool = None
        self.rotateTool = None
        self.scaleTool = None
        self.placeOnFaceTool = None
        self.tool_background = None
        self.do_button = None
        self.undo_button = None

        self.tools = []


    def init_parametres(self):
        #TODO:Add camera instance initialization
        #properties initialization
        self.xRot = 424
        self.yRot = 0
        self.zRot = 5576
        self.zoom = -39
        self.last_fps = 100.
        self.fps_count = 0
        self.fps_time = 0.


        self.oldPos3d = [.0, .0, .0]

        #self.lightAmbient = [.95, .95, .95, 1.0]
        #self.lightDiffuse = [.5, .5, .5, 1.0]
        #self.lightPossition = [29.0, -48.0, 37.0, 1.0]

        self.materialSpecular = [.0, .0, .0, 1.]
        self.materialShiness = [0.0]

        #screen properties
        self.w = 0
        self.h = 0

        #self.sceneFrameBuffer = []
        #self.tools = []


    '''
    def keyPressEvent(self, e):
        print(str(e))
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
    '''

    def keyPressEvent(self, event):
        self.controller.key_press_event(event)


    def mousePressEvent(self, event):
        self.controller.mouse_press_event(event)


    def mouseDoubleClickEvent(self, event):
        self.controller.mouse_double_click(event)

    def mouseReleaseEvent(self, event):
        self.controller.mouse_release_event(event)

    def mouseMoveEvent(self, event):
        self.controller.mouse_move_event(event)

    def wheelEvent(self, event):
        self.controller.wheel_event(event)


    def update_scene(self, reset=False):
        if reset:
            self.init_parametres()

        #self.updateGL()
        self.update()



    #TODO:All this function will be changed to control camera instance
    def set_zoom(self, diff):
        #self.camera.add_zoom(diff)
        if (self.zoom + diff >= -60.0) and (self.zoom + diff <= -5.0):
            self.zoom += diff


    def get_zoom(self):
        #return self.camera.get_zoom()
        return self.zoom

    def get_x_rotation(self):
        return self.xRot

    def get_y_rotation(self):
        return self.yRot

    def get_z_rotation(self):
        return self.zRot

    def minimumSizeHint(self):
        return QtCore.QSize(50, 50)

    def sizeHint(self):
        return QtCore.QSize(1024, 600)

    def set_x_rotation(self, angle):
        angle = self.normalize_angle_x(angle)
        if angle != self.xRot:
            self.xRot = angle
            #print("X rot: " + str(self.xRot))

    def set_y_rotation(self, angle):
        angle = self.normalize_angle(angle)
        if angle != self.yRot:
            self.yRot = angle

    def set_z_rotation(self, angle):
        angle = self.normalize_angle(angle)
        if angle != self.zRot:
            self.zRot = angle
            #print("Z rot: " + str(self.zRot))

    def texture_from_png(self, filename):
        mode_to_bpp = {'1':1, 'L':8, 'P':8, 'RGB':24, 'RGBA':32, 'CMYK':32, 'YCbCr':24, 'I':32, 'F':32}

        img = open(filename)
        img = img.transpose(FLIP_TOP_BOTTOM)
        bpp = mode_to_bpp[img.mode]
        if bpp == 32:
            type = GL_RGBA
        else:
            type = GL_RGB
        img_data = numpy.array(list(img.getdata()), numpy.uint8)

        texture = glGenTextures(1)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, type, img.size[0], img.size[1], 0, type, GL_UNSIGNED_BYTE, img_data)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        return texture

    def initializeGL(self):
        #load textures
        self.image_background = self.texture_from_png("data/img/background.png")
        #self.test_img = self.texture_from_png("data/img/test_5.png")


        #tools
        #self.selectTool = GlButton(self.texture_from_png("data/img/select_ns.png"), [3.,3.], [95.5, 18])
        #self.moveTool = GlButton(self.texture_from_png("data/img/move_ns.png"), [3.,3.], [95.5, 12.])
        self.scaleTool = GlButton(self.texture_from_png("data/img/gui/Scale_Off.png"),
                                  self.texture_from_png("data/img/gui/Scale_On.png"),
                                  self.texture_from_png("data/img/gui/Scale_Hover.png"),
                                  self.texture_from_png("data/img/gui/tool_mask.png"),
        #                          [40., 40.], [10., -200.], False,
                                  [40., 40.], [10., -245.], False,
                                  self.tr("Scale tool"),'scale')

        self.placeOnFaceTool = GlButton(self.texture_from_png("data/img/gui/PlaceOnFace_Off.png"),
                                        self.texture_from_png("data/img/gui/PlaceOnFace_On.png"),
                                        self.texture_from_png("data/img/gui/PlaceOnFace_Hover.png"),
                                        self.texture_from_png("data/img/gui/tool_mask.png"),
                                        [40., 40.], [10., -245.], False,
                                        self.tr("Place on face tool"), 'placeonface')

        self.rotateTool = GlButton(self.texture_from_png("data/img/gui/Rotate_Off.png"),
                                   self.texture_from_png("data/img/gui/Rotate_On.png"),
                                   self.texture_from_png("data/img/gui/Rotate_Hover.png"),
                                   self.texture_from_png("data/img/gui/tool_mask.png"),
                                   [40., 40.], [10., -290.], False,
                                   self.tr("Rotate tool"), 'rotate')
        self.organize_tool = GlButton(self.texture_from_png("data/img/gui/Organize_Off.png"),
                                        self.texture_from_png("data/img/gui/Organize_On.png"),
                                        self.texture_from_png("data/img/gui/Organize_Hover.png"),
                                        self.texture_from_png("data/img/gui/tool_mask.png"),
                                        [40., 40.], [10., -335.], True,
                                      self.tr("Arrange tool"), 'organize')
        self.multiply_tool = GlButton(self.texture_from_png("data/img/gui/Multi_Off.png"),
                                      self.texture_from_png("data/img/gui/Multi_On.png"),
                                      self.texture_from_png("data/img/gui/Multi_Hover.png"),
                                      self.texture_from_png("data/img/gui/tool_mask.png"),
                                      [40., 40.], [10., -380.], False,
                                      self.tr("Multiplication tool"), 'multi')

        self.support_tool = GlButton(self.texture_from_png("data/img/gui/Support_Off.png"),
                                      self.texture_from_png("data/img/gui/Support_On.png"),
                                      self.texture_from_png("data/img/gui/Support_Hover.png"),
                                      self.texture_from_png("data/img/gui/tool_mask.png"),
                                      [40., 40.], [10., -425.], False,
                                      self.tr("Support tool"), 'support')



        #back, forward buttons
        self.undo_button = GlButton(self.texture_from_png("data/img/gui/BackArrow_Off.png"),
                                    self.texture_from_png("data/img/gui/BackArrow_On.png"),
                                    self.texture_from_png("data/img/gui/BackArrow_Hover.png"),
                                    self.texture_from_png("data/img/gui/tool_mask.png"),
                                    [40., 40.], [10, -50], True,
                                    self.tr("Undo"), "undo")
        self.do_button = GlButton(self.texture_from_png("data/img/gui/ForwardArrow_Off.png"),
                                  self.texture_from_png("data/img/gui/ForwardArrow_On.png"),
                                  self.texture_from_png("data/img/gui/ForwardArrow_Hover.png"),
                                  self.texture_from_png("data/img/gui/tool_mask.png"),
                                  [40., 40.], [60, -50], True,
                                  self.tr("Do"), "do")


        #self.selectTool.set_callback(self.parent.controller.select_button_pressed)
        #self.moveTool.set_callback(self.parent.controller.move_button_pressed)
        self.rotateTool.set_callback(self.controller.rotate_button_pressed)
        self.scaleTool.set_callback(self.controller.scale_button_pressed)
        self.placeOnFaceTool.set_callback(self.controller.place_on_face_button_pressed)
        self.organize_tool.set_callback(self.controller.organize_button_pressed)

        self.support_tool.set_callback(self.controller.support_button_pressed)

        self.undo_button.set_callback(self.controller.undo_button_pressed)
        self.do_button.set_callback(self.controller.do_button_pressed)


        self.tool_background = self.texture_from_png("data/img/tool_background.png")
        self.popup_widget = self.texture_from_png("data/img/gui/popup_window.png")


        #self.tools = [self.scaleTool, self.placeOnFaceTool, self.rotateTool, self.organize_tool, self.multiply_tool, self.undo_button, self.do_button]
        #self.tools = [self.scaleTool, self.placeOnFaceTool, self.rotateTool, self.organize_tool, self.undo_button, self.do_button]
        #self.tools = [self.scaleTool, self.rotateTool, self.organize_tool, self.multiply_tool, self.support_tool, self.undo_button, self.do_button]
        self.tools = [self.scaleTool, self.rotateTool, self.organize_tool, self.undo_button, self.do_button]

        #self.tools = []

        self.bed = {}
        self.printing_space = {}

        for i in self.parent.controller.printing_parameters.get_printers_names():
            self.bed[self.parent.controller.printing_parameters.get_printer_parameters(i)['name']] = self.make_printing_bed(self.parent.controller.printing_parameters.get_printer_parameters(i))
            self.printing_space[self.parent.controller.printing_parameters.get_printer_parameters(i)['name']] = self.make_printing_space(self.parent.controller.printing_parameters.get_printer_parameters(i))

        glClearDepth(1.0)
        #glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_FALSE)
        glShadeModel(GL_FLAT)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

        #NICE
        glCullFace(GL_FRONT)

        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)

        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glEnable(GL_LIGHTING)

        #new light settings
        glLightfv(GL_LIGHT0, GL_POSITION, _gl_vector(50, 50, 100, 0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, _gl_vector(1., 1., 1., 1.))
        glLightfv(GL_LIGHT0, GL_AMBIENT, _gl_vector(0.15, 0.15, 0.15, 1.))
        #glLightfv(GL_LIGHT0, GL_SPECULAR, _gl_vector(.5, .5, 1., 1.))

        glLightfv(GL_LIGHT1, GL_POSITION, _gl_vector(100, 0, 50, 0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, _gl_vector(1., 1., 1., 1.0))
        glLightfv(GL_LIGHT1, GL_AMBIENT, _gl_vector(0.15, 0.15, 0.15, 1.))
        #glLightfv(GL_LIGHT1, GL_SPECULAR, _gl_vector(1., 1., 1., 1.))
        #new light settings

        #material
        #glMaterialfv(GL_FRONT, GL_SPECULAR, self.materialSpecular)
        #glMaterialfv(GL_FRONT, GL_SHININESS, self.materialShiness)


        glColorMaterial(GL_FRONT, GL_DIFFUSE)
        glEnable(GL_COLOR_MATERIAL)
        glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)



        glEnable(GL_MULTISAMPLE)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_NORMALIZE)


        if self.lightning_shader_program.addShaderFromSourceFile(QGLShader.Vertex, "data/shaders/lightning.vert") \
                and self.lightning_shader_program.addShaderFromSourceFile(QGLShader.Fragment, "data/shaders/lightning.frag"):
            self.lightning_shader_ok = True
            self.lightning_shader_program.log()
            self.lightning_shader_program.link()
            self.lightning_shader_program.release()


        if self.variable_layer_shader_program.addShaderFromSourceFile(QGLShader.Vertex, "data/shaders/variable_height_slic3r.vert") \
                and self.variable_layer_shader_program.addShaderFromSourceFile(QGLShader.Fragment, "data/shaders/variable_height_slic3r.frag"):
            self.variable_layer_shader_ok = True
            self.variable_layer_shader_program.log()
            self.variable_layer_shader_program.link()
            self.variable_layer_shader_program.release()



    #@timing
    def picking_render(self):
        glClearColor(0., 0., 0., 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


        glLoadIdentity()
        glTranslatef(0.0, 0.0, self.zoom)
        glRotated(-90.0, 1.0, 0.0, 0.0)
        glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)

        glTranslatef(-self.camera_position[0], -self.camera_position[1], -self.camera_position[2])

        glDisable(GL_LIGHTING)
        glDisable(GL_BLEND)

        glDisable(GL_MULTISAMPLE)

        for model in self.parent.controller.scene.models:
            if model.isVisible:
                model.render(picking=True, blending=False)

        for model in self.parent.controller.scene.models:
            if model.isVisible and model.selected:
                self.draw_tools_helper(model, self.controller.settings, True)

        if self.parent.controller.status in ['edit', 'canceled']:
            self.draw_tools(picking=True)

        glEnable(GL_MULTISAMPLE)


    def get_id_under_cursor(self, x, y):
        #print("color_picking")
        self.picking_render()
        viewport = glGetIntegerv(GL_VIEWPORT)
        color = glReadPixels(x, viewport[3] - y, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE)
        return ord(color[0])+(256*ord(color[1]))+(256*256*ord(color[2]))



    def paintGL(self, selection = 1):
        #print("Draw")
        t0 = time.time()

        if not self.bed and self.printing_space:
            return
        heat_bed = self.bed[self.controller.settings['printer']]
        printing_space = self.printing_space[self.controller.settings['printer']]
        printer = None

        #for p in self.controller.printers:
        #    if p['name'] == self.controller.settings['printer']:
        #        printer = p['printing_space']
        printer = self.controller.printing_parameters.get_printer_parameters(self.controller.actual_printer)

        model_view = self.controller.render_status in ['model_view']

        #glDepthMask(GL_TRUE)
        glEnable( GL_LIGHTING )

        glClearColor(0., 0., 0., 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.draw_background_texture()
        glLoadIdentity()

        glTranslatef(0.0, 0.0, self.zoom)
        glRotated(-90.0, 1.0, 0.0, 0.0)
        glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)

        glTranslatef(-self.camera_position[0], -self.camera_position[1], -self.camera_position[2])

        if self.xRot < 0:
            glEnable(GL_BLEND)
            glDisable(GL_DEPTH_TEST)
            glCallList(heat_bed)
            glDisable(GL_BLEND)
        else:
            glDisable(GL_BLEND)
            glCallList(heat_bed)



        glEnable(GL_DEPTH_TEST)

        if model_view:
            #render solid objects, possible to edit transformation, select objects
            for model in self.parent.controller.scene.models:
                if model.isVisible:
                    if model.selected and self.controller.advance_settings:
                        if self.variable_layer_shader_ok:
                            self.variable_layer_shader_program.bind()
                            self.variable_layer_shader_program.setUniformValue("height_of_object", model.size[2])
                            self.variable_layer_shader_program.setUniformValue("z_cursor", model.z_cursor*.1)
                            self.variable_layer_shader_program.setUniformValue("z_cursor_band_width", 0.75)
                            #self.variable_layer_shader_program.setUniformValueArray(self.z_texture)

                            #glActiveTexture(GL_TEXTURE0)
                            glBindTexture(GL_TEXTURE_2D, model.variable_texture)
                            #glBindTexture(GL_TEXTURE_2D, self.test_img)
                            self.variable_layer_shader_program.setUniformValue("z_texture", 0)
                            self.variable_layer_shader_program.setUniformValue("z_to_texture_row",
                                                                               (model.size[2]/self.controller.resolution_of_texture*self.controller.resolution_of_texture))
                                                                               #(self.controller.resolution_of_texture * self.controller.resolution_of_texture)/(self.controller.resolution_of_texture*model.size[2]))
                            #self.variable_layer_shader_program.setUniformValue("z_to_texture_row",
                            #                                                   0.195)
                            self.variable_layer_shader_program.setUniformValue("z_texture_row_to_normalized", 1./self.controller.resolution_of_texture)
                        model.render(picking=False, blending=not model_view)
                        if self.variable_layer_shader_ok:
                            self.variable_layer_shader_program.release()
                    else:
                        if self.lightning_shader_ok:
                            self.lightning_shader_program.bind()
                        model.render(picking=False, blending=not model_view)
                        if self.lightning_shader_ok:
                            self.lightning_shader_program.release()


            if not self.controller.advance_settings:
                for support in self.parent.controller.scene.supports:
                    self.draw_support(support)


            if self.parent.controller.settings['toolButtons']['supportButton'] and self.parent.controller.scene.actual_support:
                print("Support height: " + str(self.parent.controller.scene.actual_support['height']))
                self.draw_support(self.parent.controller.scene.actual_support)

            for model in self.parent.controller.scene.models:
                if model.isVisible and model.selected:
                    self.draw_tools_helper(model, self.parent.controller.settings)

            glCallList(printing_space)

            if self.parent.controller.status in ['edit', 'canceled']:
                self.draw_tools()

        elif not model_view:
            #render blended objects and layers of gcode to inspect it
            #glEnable(GL_LIGHTING)
            for model in self.parent.controller.scene.models:
                if model.isVisible:
                    if self.lightning_shader_ok:
                        self.lightning_shader_program.bind()
                    model.render(picking=False, blending=not model_view)
                    if self.lightning_shader_ok:
                        self.lightning_shader_program.release()
            #glDisable(GL_LIGHTING)

            color_change_list = [i['value'] for i in self.parent.gcode_slider.points if not i['value'] == -1]

            color = [13, 82, 78]
            for color_change in color_change_list:
                self.draw_layer(color_change, color, printer)
                #Add text note for ColorChange


            color = [255, 97, 0]
            self.draw_layer(self.controller.gcode_layer, color, printer)
            glCallList(printing_space)

        self.draw_axis(self.parent.controller.printing_parameters.get_printer_parameters(self.controller.settings['printer'])['printing_space'])

        self.draw_warning_window()

        if self.controller.status == 'generated':
            self.draw_information_window()

        #if self.controller.settings['debug']:
        #    self.picking_render()

        if self.controller.settings['debug']:
            print("draw_debug")
            self.draw_debug()

        glFlush()

        t1 = time.time()

        if self.controller.settings['debug']:
            if self.fps_count==100:
                self.last_fps = 1./(self.fps_time/self.fps_count)
                self.fps_count = 0
                self.fps_time = 0.
                self.renderText(100, 100, 'FPS: %3.1f' % self.last_fps)
            else:
                self.fps_count+=1
                self.fps_time+=t1-t0
                self.renderText(100, 100, 'FPS: %3.1f' % self.last_fps)


    def draw_support(self, support):
        pos = support['pos']
        height = support['height']

        glPushMatrix()
        glTranslatef(pos[0], pos[1], 0.0)
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        glLineWidth(2.5)
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 0.0, height)
        glEnd()

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glPopMatrix()


    def draw_warning_window(self):
        #set camera view
        messages = self.controller.scene.get_warnings()
        if len(messages) > 0:
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            viewport = glGetIntegerv(GL_VIEWPORT)
            glOrtho(0.0, viewport[2], 0.0, viewport[3], -1.0, 1.0)
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()

            sW = viewport[2] * 1.0
            sH = viewport[3] * 1.0

            glLoadIdentity()
            glDisable(GL_LIGHTING)
            glDisable(GL_DEPTH_TEST)
            glEnable(GL_TEXTURE_2D)

            #draw frame for warning messages
            position_x = 25
            position_y = 25
            size_w = 325
            size_h = 180

            coef_sH = size_h
            coef_sW = size_w

            glBindTexture(GL_TEXTURE_2D, self.popup_widget)
            glColor4f(0.1, 0.1, 0.1, .75)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0)
            glVertex3f(position_x, position_y, 0)
            glTexCoord2f(0, 1)
            glVertex3f(position_x, (position_y + coef_sH), 0)
            glTexCoord2f(1, 1)
            glVertex3f((position_x + coef_sW), (position_y + coef_sH), 0)
            glTexCoord2f(1, 0)
            glVertex3f((position_x + coef_sW), position_y, 0)
            glEnd()

            glDisable(GL_TEXTURE_2D)

            glColor4f(1.,1.,1.,1.)
            font = self.controller.view.font
            font.setPointSize(25*self.controller.dpi_coef - self.controller.dpi_scale)
            self.renderText(115, sH - 153, u"WARNING", font)

            font.setPointSize(8*self.controller.dpi_coef - self.controller.dpi_scale)
            for n, message in enumerate(messages):
                #Maximum of massages in warning box
                if n > 5:
                    break
                self.renderText(57, sH-122+15*n,  message, font)

            glEnable(GL_DEPTH_TEST)

            glPopMatrix()

            glMatrixMode(GL_PROJECTION)
            glPopMatrix()

            glMatrixMode(GL_MODELVIEW)


    def draw_information_window(self):
        # set camera view
        messages = self.controller.get_informations()

        if len(messages) > 0:
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            viewport = glGetIntegerv(GL_VIEWPORT)
            glOrtho(0.0, viewport[2], 0.0, viewport[3], -1.0, 1.0)
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()

            sW = viewport[2] * 1.0
            sH = viewport[3] * 1.0

            glLoadIdentity()
            glDisable(GL_LIGHTING)
            glDisable(GL_DEPTH_TEST)
            glEnable(GL_TEXTURE_2D)

            # draw frame for information messages
            position = [-325, 25]

            position_x = sW - abs(position[0]) if position[0] < 0 else position[0]
            position_y = sH - abs(position[1]) if position[1] < 0 else position[1]

            #position_x = 25
            #position_y = 25

            size_w = 300
            size_h = 100

            coef_sH = size_h
            coef_sW = size_w

            glBindTexture(GL_TEXTURE_2D, self.popup_widget)
            glColor4f(0.1, 0.1, 0.1, .75)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0)
            glVertex3f(position_x, position_y, 0)
            glTexCoord2f(0, 1)
            glVertex3f(position_x, (position_y + coef_sH), 0)
            glTexCoord2f(1, 1)
            glVertex3f((position_x + coef_sW), (position_y + coef_sH), 0)
            glTexCoord2f(1, 0)
            glVertex3f((position_x + coef_sW), position_y, 0)
            glEnd()

            glDisable(GL_TEXTURE_2D)

            glColor4f(1., 1., 1., 1.)
            font = self.controller.view.font
            font.setPointSize(17 *self.controller.dpi_coef - self.controller.dpi_scale)
            self.renderText(position_x + 8, sH - position_y - size_h + 30, u"PRINT INFO", font)

            font.setPointSize(9 *self.controller.dpi_coef - self.controller.dpi_scale)

            #header = '{:>20}{:>10}{:>14}'.format(' ', 'time:', 'filament:')
            #print(header)
            #text = '{:20}{:>10}{:>12}'.format(messages['info_text'], messages['printing_time'], messages['filament_lenght'])
            #print(text)
            glColor3f(.5,.5,.5)
            #self.renderText(position_x + 8, sH - position_y - size_h + 63, header, font)
            self.renderText(position_x + 108, sH - position_y - size_h + 63, self.tr("estimate time:"), font)
            self.renderText(position_x + 208, sH - position_y - size_h + 63, self.tr("filament:"), font)
            glColor3f(1., 1., 1.)
            #self.renderText(position_x + 8, sH - position_y - size_h + 65 + 15, text, font)
            self.renderText(position_x + 10, sH - position_y - size_h + 65 + 15, messages['info_text'], font)
            self.renderText(position_x + 108, sH - position_y - size_h + 65 + 15, messages['printing_time'], font)
            self.renderText(position_x + 208, sH - position_y - size_h + 65 + 15, messages['filament_lenght'], font)


            glEnable(GL_DEPTH_TEST)

            glPopMatrix()

            glMatrixMode(GL_PROJECTION)
            glPopMatrix()

            glMatrixMode(GL_MODELVIEW)

    def draw_layer(self, layer, color, printer):
        printing_space = printer['printing_space']
        layer_data = self.controller.gcode.data[layer]

        line_width = .01
        left = True

        glPushMatrix()
        #TODO: Better solution
        glTranslatef(printing_space[0]*-0.5*.1, printing_space[1]*-0.5*.1, 0.0)

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        glLineWidth(1.0)

        #glEnable(GL_LINE_SMOOTH)
        #glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)


        glBegin(GL_LINES)
        #for layer_data in layer_datas:
        #( brim, perimetry,  infill, support, colorchange)
        for p in layer_data:
            if 'E-sk' in p[2]:
                color = [255, 255, 255]
            elif 'E-su' in p[2]:
                color = [88, 117, 69]
            elif 'E-i' in p[2]:
                color = [ 255,158, 60]
            elif 'E-p' in p[2]:
                color = [247, 108, 49]
            if 'E' in p[2]:
                glColor3ub(color[0], color[1], color[2])
                glVertex3f(p[0][0] * .1, p[0][1] * .1, p[0][2] * .1)
                glVertex3f(p[1][0] * .1, p[1][1] * .1, p[1][2] * .1)
            #elif p[2] == 'M':
            #    glColor3f(0.0, 0.0, 1.0)
            #    glVertex3f(p[0][0] * .1, p[0][1] * .1, p[0][2] * .1)
            #    glVertex3f(p[1][0] * .1, p[1][1] * .1, p[1][2] * .1)
        glEnd()


        #glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        glBegin(GL_TRIANGLE_STRIP)
        #glBegin(GL_TRIANGLES)
        # for layer_data in layer_datas:

        last_type = 'E'
        for p in layer_data:
            a = numpy.array(p[0])
            b = numpy.array(p[1])
            a *= .1
            b *= .1
            ab_leng = numpy.linalg.norm(b-a)

            dx = b[0] - a[0] #x2-x1
            dy = b[1] - a[1] #y2-y1
            n1 = numpy.array([-dy, dx, 0.0])
            n1 /= numpy.linalg.norm(n1)
            n2 = numpy.array([dy, -dx, 0.0])
            n2 /= numpy.linalg.norm(n2)

            if not last_type == p[2]:
                glEnd()
                glBegin(GL_TRIANGLE_STRIP)
                last_type = p[2]

            if 'M' == p[2]:
                continue

            if 'E-sk' == p[2]:
                glColor3ub(255, 255, 255)
            elif 'E-su' == p[2]:
                glColor3ub(88, 117, 69)
            elif 'E-i' == p[2]:
                glColor3ub(255, 158, 60)
            elif 'E-p' == p[2]:
                glColor3ub(247, 108, 49)

            a00 = a + n2 * ((p[4]*.025)/ab_leng)
            a01 = a + n1 * ((p[4]*.025)/ab_leng)

            b00 = b + n2 * ((p[4]*.025)/ab_leng)
            b01 = b + n1 * ((p[4]*.025)/ab_leng)

            glVertex3f(a00[0], a00[1], p[0][2]*.1)
            glVertex3f(a01[0], a01[1], p[0][2]*.1)

            glVertex3f(b00[0], b00[1], p[1][2]*.1)
            glVertex3f(b01[0], b01[1], p[1][2]*.1)
        glEnd()

        #glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glPopMatrix()


    def draw_tools_helper(self, model, settings, picking=False):
        if picking:
            rotateColors = [model.rotateColorXId, model.rotateColorYId, model.rotateColorZId]
            scaleColors = [model.scaleColorXId, model.scaleColorYId, model.scaleColorZId, model.scaleColorXYZId]
        else:
            rotateColors = [[180,180,180],[180,180,180],[180,180,180]]
            scaleColors = [model.scaleColorXId, model.scaleColorYId, model.scaleColorZId, model.scaleColorXYZId]

        if self.rotateTool.is_pressed():
        #if settings['toolButtons']['rotateButton']:
            #self.draw_rotation_circle(model, rotateColors, [i + o for i,o in zip(model.boundingSphereCenter, model.pos)], model.boundingSphereSize, picking)
            self.draw_rotation_circle(model, rotateColors, model.pos, model.boundingSphereSize, picking)
        if self.scaleTool.is_pressed():
        #elif settings['toolButtons']['scaleButton']:
            self.draw_scale_rect(model, scaleColors, model.pos, model.boundingSphereSize, picking)


    def draw_scale_rect(self, model, colors, position, radius, picking=False):
        if not picking:
                colors[3] = [255, 255, 255]

        offset=0.5
        size_of_selector = 0.2

        min = deepcopy(model.min)
        max = deepcopy(model.max)

        min -= offset
        max += offset

        glPushMatrix()
        glTranslatef(position[0], position[1], 0.0)
        glDisable( GL_LIGHTING )
        glDisable(GL_DEPTH_TEST)


        if picking:
            glColor3ubv(colors[3])

            glBegin(GL_TRIANGLES)
            glVertex3f(max[0] - size_of_selector, max[1] - size_of_selector, 0.)
            glVertex3f(max[0] - size_of_selector, max[1] + size_of_selector, 0.)
            glVertex3f(max[0] + size_of_selector, max[1] + size_of_selector, 0.)

            glVertex3f(max[0] + size_of_selector, max[1] + size_of_selector, 0.)
            glVertex3f(max[0] + size_of_selector, max[1] - size_of_selector, 0.)
            glVertex3f(max[0] - size_of_selector, max[1] - size_of_selector, 0.)
            glEnd()

            glBegin(GL_TRIANGLES)
            glVertex3f(min[0] - size_of_selector, min[1] - size_of_selector, 0.)
            glVertex3f(min[0] - size_of_selector, min[1] + size_of_selector, 0.)
            glVertex3f(min[0] + size_of_selector, min[1] + size_of_selector, 0.)

            glVertex3f(min[0] + size_of_selector, min[1] + size_of_selector, 0.)
            glVertex3f(min[0] + size_of_selector, min[1] - size_of_selector, 0.)
            glVertex3f(min[0] - size_of_selector, min[1] - size_of_selector, 0.)
            glEnd()

            glBegin(GL_TRIANGLES)
            glVertex3f(max[0] - size_of_selector, min[1] - size_of_selector, 0.)
            glVertex3f(max[0] + size_of_selector, min[1] - size_of_selector, 0.)
            glVertex3f(max[0] - size_of_selector, min[1] + size_of_selector, 0.)

            glVertex3f(max[0] + size_of_selector, min[1] + size_of_selector, 0.)
            glVertex3f(max[0] + size_of_selector, min[1] - size_of_selector, 0.)
            glVertex3f(max[0] - size_of_selector, min[1] + size_of_selector, 0.)
            glEnd()

            glBegin(GL_TRIANGLES)
            glVertex3f(min[0] - size_of_selector, max[1] - size_of_selector, 0.)
            glVertex3f(min[0] + size_of_selector, max[1] - size_of_selector, 0.)
            glVertex3f(min[0] - size_of_selector, max[1] + size_of_selector, 0.)

            glVertex3f(min[0] + size_of_selector, max[1] + size_of_selector, 0.)
            glVertex3f(min[0] - size_of_selector, max[1] + size_of_selector, 0.)
            glVertex3f(min[0] + size_of_selector, max[1] - size_of_selector, 0.)
            glEnd()


        else:
            glColor3ubv(colors[3])
            #Outer lines

            glBegin(GL_LINE_LOOP)
            glVertex3f(min[0], min[1], 0.)
            glVertex3f(min[0], max[1], 0.)
            glVertex3f(max[0], max[1], 0.)
            glVertex3f(max[0], min[1], 0.)
            glEnd()

            if model.scaleAxis == 'XYZ':
                glColor3ub(255, 97, 0)
            else:
                glColor3f(1.,1.,1.)
            glBegin(GL_TRIANGLES)
            glVertex3f(max[0] - size_of_selector, max[1] - size_of_selector, 0.)
            glVertex3f(max[0] - size_of_selector, max[1] + size_of_selector, 0.)
            glVertex3f(max[0] + size_of_selector, max[1] + size_of_selector, 0.)

            glVertex3f(max[0] + size_of_selector, max[1] + size_of_selector, 0.)
            glVertex3f(max[0] + size_of_selector, max[1] - size_of_selector, 0.)
            glVertex3f(max[0] - size_of_selector, max[1] - size_of_selector, 0.)
            glEnd()

            glBegin(GL_TRIANGLES)
            glVertex3f(min[0] - size_of_selector, min[1] - size_of_selector, 0.)
            glVertex3f(min[0] - size_of_selector, min[1] + size_of_selector, 0.)
            glVertex3f(min[0] + size_of_selector, min[1] + size_of_selector, 0.)

            glVertex3f(min[0] + size_of_selector, min[1] + size_of_selector, 0.)
            glVertex3f(min[0] + size_of_selector, min[1] - size_of_selector, 0.)
            glVertex3f(min[0] - size_of_selector, min[1] - size_of_selector, 0.)
            glEnd()

            glBegin(GL_TRIANGLES)
            glVertex3f(max[0] - size_of_selector, min[1] - size_of_selector, 0.)
            glVertex3f(max[0] + size_of_selector, min[1] - size_of_selector, 0.)
            glVertex3f(max[0] - size_of_selector, min[1] + size_of_selector, 0.)

            glVertex3f(max[0] + size_of_selector, min[1] + size_of_selector, 0.)
            glVertex3f(max[0] + size_of_selector, min[1] - size_of_selector, 0.)
            glVertex3f(max[0] - size_of_selector, min[1] + size_of_selector, 0.)
            glEnd()

            glBegin(GL_TRIANGLES)
            glVertex3f(min[0] - size_of_selector, max[1] - size_of_selector, 0.)
            glVertex3f(min[0] + size_of_selector, max[1] - size_of_selector, 0.)
            glVertex3f(min[0] - size_of_selector, max[1] + size_of_selector, 0.)

            glVertex3f(min[0] + size_of_selector, max[1] + size_of_selector, 0.)
            glVertex3f(min[0] - size_of_selector, max[1] + size_of_selector, 0.)
            glVertex3f(min[0] + size_of_selector, max[1] - size_of_selector, 0.)
            glEnd()



            #self.renderText(0., 0., 0., "%s" % str(model.size_origin))


        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glPopMatrix()


    def draw_rotation_circle(self, model, colors, position, radius, picking=False):
        actual_angle = numpy.rad2deg(model.rot[2])
        if actual_angle >= 360.:
            n, actual_angle = divmod(actual_angle, 360)
        elif actual_angle <= 0.:
            n, actual_angle = divmod(actual_angle, -360)

        if not picking:
                colors[2] = [255, 255, 255]

        segments = 64
        if picking:
            width = 0.45
        else:
            width = 0.15

        if radius < 2.5:
            radius = 2.5

        r0 = radius-0.4
        r1 = radius-0.05
        r2 = radius
        r3 = radius+0.05
        r4 = radius+0.15
        r5 = radius+0.25
        r6 = radius+0.4
        r7 = radius+1.0

        if picking:
            list_of_segnments_6 = numpy.arange(0., 360., 1.)
            circle7 = [[numpy.cos(numpy.radians(i)) * r7, numpy.sin(numpy.radians(i)) * r7] for i in list_of_segnments_6]
        else:
            #calculete points for circle 0 and 1
            list_of_segnments_0_1 = numpy.arange(0, 360., 360./16.)
            circle0 = [[numpy.cos(numpy.radians(i)) * r0, numpy.sin(numpy.radians(i)) * r0] for i in list_of_segnments_0_1]
            circle1 = [[numpy.cos(numpy.radians(i)) * r1, numpy.sin(numpy.radians(i)) * r1] for i in list_of_segnments_0_1]

            # calculete points for circle 2
            list_of_segnments_2 = numpy.arange(0, 360., 360. / segments)
            circle2 = [[numpy.cos(numpy.radians(i)) * r2, numpy.sin(numpy.radians(i)) * r2] for i in list_of_segnments_2]

            # calculete points for circle 3, 4 and 5
            list_of_segnments_3_4_5 = numpy.arange(0, 360., 360. / 72.)
            circle3 = [[numpy.cos(numpy.radians(i)) * r3, numpy.sin(numpy.radians(i)) * r3] for i in list_of_segnments_3_4_5]
            circle4 = [[numpy.cos(numpy.radians(i)) * r4, numpy.sin(numpy.radians(i)) * r4] for i in list_of_segnments_3_4_5]
            circle5 = [[numpy.cos(numpy.radians(i)) * r5, numpy.sin(numpy.radians(i)) * r5] for i in list_of_segnments_3_4_5]

            # calculete points for circle 6
            list_of_segnments_6 = numpy.arange(0., 360., 1.)
            circle6 = [[numpy.cos(numpy.radians(i)) * r6, numpy.sin(numpy.radians(i)) * r6] for i in list_of_segnments_6]
            circle7 = [[numpy.cos(numpy.radians(i)) * r7, numpy.sin(numpy.radians(i)) * r7] for i in list_of_segnments_6]

        glPushMatrix()
        glTranslatef(position[0], position[1], 0.0)
        glDisable( GL_LIGHTING )
        glDisable(GL_DEPTH_TEST)


        if picking:
            glColor3ubv(colors[2])
            if picking:
                glLineWidth(5)
            else:
                glLineWidth(2.5)
            glBegin(GL_LINES)
            glVertex3f(0., 0., 0.)
            glVertex3f(circle7[int(actual_angle)][0], circle7[int(actual_angle)][1] * -1., 0.)
            glEnd()

        else:
            glColor3ubv(colors[2])
            #inner lines
            glBegin(GL_LINES)
            for i0, i1 in zip(circle0, circle1):
                glVertex3f(i0[0], i0[1], 0.)
                glVertex3f(i1[0], i1[1], 0.)
            glEnd()

            #outer lines
            bigger_index = list(xrange(0,72,3))
            glBegin(GL_LINES)
            for n, (i0, i1, i2) in enumerate(zip(circle3, circle4, circle5)):
                glVertex3f(i0[0], i0[1], 0.)
                if n in bigger_index:
                    glVertex3f(i2[0], i2[1], 0.)
                else:
                    glVertex3f(i1[0], i1[1], 0.)
            glEnd()

            #main circle
            glBegin(GL_LINE_LOOP)
            for i in circle2:
                glVertex3f(i[0], i[1], 0.)
            glEnd()

            #print("sceneRender: " + str(actual_angle))
            if model.rotationAxis == "Z":
                glLineWidth(5)
                glColor3ub(255, 97, 0)
            else:
                glLineWidth(2.5)
                glColor3ub(255, 255, 255)
            glBegin(GL_LINES)
            glVertex3f(0., 0., 0.)
            glVertex3f(circle7[int(actual_angle)][0], circle7[int(actual_angle)][1]*-1., 0.)
            glEnd()


            glLineWidth(2.5)
            glBegin(GL_LINE_LOOP)
            glVertex3f(0., 0., 0.)
            glVertex3f(circle6[0][0], circle6[0][1], 0.)
            glColor3ub(255, 97, 0)
            for i in circle6[1:int(actual_angle)+1]:
                glVertex3f(i[0], i[1]*-1., 0.)
                #glVertex3f(self.hitPoint[0], self.hitPoint[1], self.hitPoint[2])
            glColor3ub(255, 255, 255)
            glVertex3f(0., 0., 0.)
            glEnd()

            self.renderText(circle7[int(actual_angle)][0], circle7[int(actual_angle)][1]*-1., 0., "%.1f" % actual_angle )


        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glPopMatrix()


    def draw_debug(self):
        glPushMatrix()
        glDisable(GL_LIGHTING)
        glColor3f(1.,.0,.0)
        glBegin(GL_LINES)
        glVertex3f(self.rayStart[0], self.rayStart[1], self.rayStart[2])
        glVertex3f(self.rayDir[0]+self.rayStart[0], self.rayDir[1]+self.rayStart[1], self.rayDir[2]+self.rayStart[2])
        '''
        glColor3f(0.,1.0,.0)
        glVertex3f(self.rayStart[0], self.rayStart[1], self.rayStart[2])
        glVertex3f(self.rayUp[0], self.rayUp[1], self.rayUp[2])
        glColor3f(0.,.0,.1)
        glVertex3f(self.rayStart[0], self.rayStart[1], self.rayStart[2])
        glVertex3f(self.rayRight[0], self.rayRight[1], self.rayRight[2])
        '''
        glEnd()

        glBegin(GL_LINE_LOOP)
        glVertex3f(self.v0[0], self.v0[1], self.v0[2])
        glVertex3f(self.v1[0], self.v1[1], self.v1[2])
        glVertex3f(self.v2[0], self.v2[1], self.v2[2])
        glEnd()

        glEnable(GL_LIGHTING)
        glPopMatrix()


    def resizeGL(self, width, height):
        self.w = width
        self.h = height
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45., float(width*1./height*1.), 1., 75.)
        glMatrixMode(GL_MODELVIEW)

    def get_cursor_position(self, event):
        matModelView = glGetDoublev(GL_MODELVIEW_MATRIX )
        matProjection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv( GL_VIEWPORT )

        winX = event.x() * 1.0
        winY = viewport[3] - (event.y() *1.0)

        rayStart = gluUnProject(winX, winY, -1.0, matModelView, matProjection, viewport)
        rayEnd = gluUnProject(winX, winY, 1.0, matModelView, matProjection, viewport)

        return (rayStart, rayEnd)

    def get_camera_direction(self, event):
        matModelView = glGetDoublev(GL_MODELVIEW_MATRIX )
        matProjection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv( GL_VIEWPORT )

        winX = (viewport[2]*.5)
        winY = (viewport[3]*.5)

        rayStart = numpy.array(gluUnProject(winX, winY, 0.0, matModelView, matProjection, viewport))
        rayEnd = numpy.array(gluUnProject(winX, winY, 1.0, matModelView, matProjection, viewport))

        rayUp = numpy.array(gluUnProject(winX, winY + 10., 0.0, matModelView, matProjection, viewport))
        rayUp = rayUp - rayStart
        rayUp /= numpy.linalg.norm(rayUp)
        self.rayUp = rayUp

        rayRight = numpy.array(gluUnProject(winX + 10., winY, 0.0, matModelView, matProjection, viewport))
        rayRight = rayRight - rayStart
        rayRight /= numpy.linalg.norm(rayRight)
        self.rayRight = rayRight
        '''
        self.rayStart = rayStart
        self.rayDir = (rayEnd - rayStart)/(numpy.linalg.norm(rayEnd - rayStart))
        self.rayUp = rayUp
        self.rayRight = rayRight
        '''

        rayDir = (rayEnd - rayStart)/(numpy.linalg.norm(rayEnd - rayStart))

        return rayStart, rayDir, rayUp, rayRight



    def make_printing_bed(self, printer_data):
        #print("Printer data: " + str(printer_data))
        #Model = ModelTypeStl.load(printer_data['model'])
        Model = ModelTypeObj.load(printer_data['model'])
        bed_texture = printer_data['texture']
        printing_space = printer_data['printing_space']

        image_hotbed = self.texture_from_png(bed_texture)

        genList = glGenLists(1)
        glNewList(genList, GL_COMPILE)

        glLineWidth(2)
        glPushMatrix()
        glTranslatef(printer_data['model_offset'][0], printer_data['model_offset'][1], printer_data['model_offset'][2])

        glDisable(GL_BLEND)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, image_hotbed)

        glEnable(GL_LIGHTING)

        #glShadeModel(GL_SMOOTH)
        glCullFace(GL_FRONT_AND_BACK)

        #Obj version
        #glColor4f(.4, .4, .4, .75)
        glColor4f(1., 1., 1., 1.)
        glBegin(GL_TRIANGLES)
        for i in xrange(0, len(Model.v0)):
            #print(str(Model.v0[i]))
            glTexCoord2f(Model.t0[i][0], Model.t0[i][1])
            glNormal3f(Model.n0[i][0], Model.n0[i][1], Model.n0[i][2])
            glVertex3f(Model.v0[i][0]*.1, Model.v0[i][1]*.1, Model.v0[i][2]*.1)

            glTexCoord2f(Model.t1[i][0], Model.t1[i][1])
            glNormal3f(Model.n1[i][0], Model.n1[i][1], Model.n1[i][2])
            glVertex3f(Model.v1[i][0]*.1, Model.v1[i][1]*.1, Model.v1[i][2]*.1)

            glTexCoord2f(Model.t2[i][0], Model.t2[i][1])
            glNormal3f(Model.n2[i][0], Model.n2[i][1], Model.n2[i][2])
            glVertex3f(Model.v2[i][0]*.1, Model.v2[i][1]*.1, Model.v2[i][2]*.1)
        glEnd()

        glPopMatrix()

        #glEnable(GL_TEXTURE_2D)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_LIGHTING)
        glEndList()


        return genList

    def make_printing_space(self, printer_data):
        printing_space = printer_data['printing_space']

        genList = glGenLists(1)
        glNewList(genList, GL_COMPILE)

        glLineWidth(.75)
        glEnable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_LIGHTING)

        glEnable(GL_DEPTH_TEST)

        glBegin(GL_LINES)
        glColor3f(1, 1, 1)
        glVertex3d(printing_space[0] * -0.5 * .1, printing_space[1] * 0.5 * .1, 0)
        glVertex3d(printing_space[0] * -0.5 * .1, printing_space[1] * 0.5 * .1, printing_space[2] * .1)

        glVertex3d(printing_space[0] * 0.5 * .1, printing_space[1] * 0.5 * .1, 0)
        glVertex3d(printing_space[0] * 0.5 * .1, printing_space[1] * 0.5 * .1, printing_space[2] * .1)

        glVertex3d(printing_space[0] * 0.5 * .1, printing_space[1] * -0.5 * .1, 0)
        glVertex3d(printing_space[0] * 0.5 * .1, printing_space[1] * -0.5 * .1, printing_space[2] * .1)

        glVertex3d(printing_space[0] * -0.5 * .1, printing_space[1] * -0.5 * .1, 0)
        glVertex3d(printing_space[0] * -0.5 * .1, printing_space[1] * -0.5 * .1, printing_space[2] * .1)
        glEnd()

        glBegin(GL_LINE_LOOP)
        glVertex3d(printing_space[0] * -0.5 * .1, printing_space[1] * 0.5 * .1, printing_space[2] * .1)
        glVertex3d(printing_space[0] * 0.5 * .1, printing_space[1] * 0.5 * .1, printing_space[2] * .1)
        glVertex3d(printing_space[0] * 0.5 * .1, printing_space[1] * -0.5 * .1, printing_space[2] * .1)
        glVertex3d(printing_space[0] * -0.5 * .1, printing_space[1] * -0.5 * .1, printing_space[2] * .1)
        glEnd()
        glEndList()



        return genList

    def draw_axis(self, printing_space):
        glLineWidth(5)
        #glDisable(GL_DEPTH_TEST)
        glBegin(GL_LINES)
        glColor3f(1, 0, 0)
        glVertex3d(printing_space[0] * -0.5 * .1, printing_space[1] * -0.5 * .1, 0)
        glVertex3d((printing_space[0] * -0.5 * .1) + 1, printing_space[1] * -0.5 * .1, 0)

        glColor3f(0, 1, 0)
        glVertex3d(printing_space[0] * -0.5 * .1, printing_space[1] * -0.5 * .1, 0)
        glVertex3d(printing_space[0] * -0.5 * .1, (printing_space[1] * -0.5 * .1) + 1, 0)

        glColor3f(0, 0, 1)
        glVertex3d(printing_space[0] * -0.5 * .1, printing_space[1] * -0.5 * .1, 0)
        glVertex3d(printing_space[0] * -0.5 * .1, printing_space[1] * -0.5 * .1, 1)
        glEnd()

        glColor3f(1, 0, 0)
        self.renderText((printing_space[0] * -0.5 * .1) + 1.1, printing_space[1] * -0.5 * .1, 0, "X")
        glColor3f(0, 1, 0)
        self.renderText(printing_space[0] * -0.5 * .1, (printing_space[1] * -0.5 * .1) + 1.1, 0, "Y")
        glColor3f(0, 0, 1)
        self.renderText(printing_space[0] * -0.5 * .1, printing_space[1] * -0.5 * .1, 1.1, "Z")

        #glEnable(GL_DEPTH_TEST)


    def draw_background_texture(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        viewport = glGetIntegerv( GL_VIEWPORT )
        glOrtho(0.0, viewport[2], 0.0, viewport[3], 0.0, 1.0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()

        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)

        glColor3f(1,1,1)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.image_background)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(0, 0, 0)

        glTexCoord2f(0, 1)
        glVertex3f(0, viewport[3], 0)

        glTexCoord2f(1, 1)
        glVertex3f(viewport[2], viewport[3], 0)

        glTexCoord2f(1, 0)
        glVertex3f(viewport[2], 0, 0)
        glEnd()

        glEnable(GL_DEPTH_TEST)

        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)

    def draw_tools(self, picking=False):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        viewport = glGetIntegerv( GL_VIEWPORT )
        glOrtho(0.0, viewport[2], 0.0, viewport[3], -1.0, 1.0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()

        sW = viewport[2] * 1.0
        sH = viewport[3] * 1.0

        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        glEnable(GL_BLEND)
        glColor3f(1,1,1)

        size = 45.

        coef_sH = 50
        coef_sW = 50

        for tool in self.tools:
            position_x = sW - abs(tool.position[0]) if tool.position[0] < 0 else tool.position[0]
            position_y = sH - abs(tool.position[1]) if tool.position[1] < 0 else tool.position[1]

            coef_sW = tool.size[0]
            coef_sH = tool.size[1]

            if picking:
                glColor3ub(tool.color_id[0], tool.color_id[1], tool.color_id[2])
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, tool.texture_background)
            else:
                glColor3f(1,1,1)
                glEnable(GL_TEXTURE_2D)
                if tool.pressed:
                    glBindTexture(GL_TEXTURE_2D, tool.texture_on)
                elif tool.mouse_over:
                    glColor3f(1, 1, 1)
                    glBindTexture(GL_TEXTURE_2D, tool.texture_hover)
                else:
                    glBindTexture(GL_TEXTURE_2D, tool.texture_off)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0)
            glVertex3f(position_x, position_y, 0)
            glTexCoord2f(0, 1.)
            glVertex3f(position_x, (position_y + coef_sH), 0)
            glTexCoord2f(1., 1.)
            glVertex3f((position_x + coef_sW), (position_y + coef_sH), 0)
            glTexCoord2f(1., 0)
            glVertex3f((position_x + coef_sW), position_y, 0)
            glEnd()


        glEnable(GL_DEPTH_TEST)

        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)


    def normalize_angle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle

    def normalize_angle_x(self, angle):
        if angle < -90*16:
            angle = -90*16
        if angle > 90*16:
            angle = 90*16
        return angle


def _gl_vector(array, *args):
    '''
    Convert an array and an optional set of args into a flat vector of GLfloat
    '''
    array = numpy.array(array)
    if len(args) > 0:
        array = numpy.append(array, args)
    vector = (GLfloat * len(array))(*array)
    return vector