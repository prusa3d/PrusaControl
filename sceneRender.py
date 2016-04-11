# -*- coding: utf-8 -*-
import logging
from OpenGL.GL import *
from OpenGL.GLU import *

import math

import numpy
from PyQt4.QtGui import QImage, QColor
from PyQt4.QtOpenGL import *
from PyQt4 import QtCore

from Image import *




class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        QGLWidget.__init__(self, parent)
        #TODO:Add camera instance
        self.parent = parent
        self.initParametres()

        #properties definition
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.zoom = 0

        self.oldPos3d = [.0, .0, .0]

        self.lightAmbient = [.0, .0, .0, .0]
        self.lightDiffuse = [.0, .0, .0, .0]
        self.lightPossition = [.0, .0, .0, .0]

        self.materialSpecular = [.0,.0,.0,.0]
        self.materialShiness = [.0]

        #screen properties
        self.w = 0
        self.h = 0

        self.initParametres()

        self.sceneFrameBuffer = []
        self.image_background = []

    def initParametres(self):
        #TODO:Add camera instance initialization
        #properties initialization
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.zoom = -15

        self.oldPos3d = [.0, .0, .0]

        self.lightAmbient = [.95, .95, .95, 1.0]
        self.lightDiffuse = [.5, .5, .5, 1.0]
        self.lightPossition = [29.0, -48.0, 37.0, 1.0]

        self.materialSpecular = [.05,.05,.05,.1]
        self.materialShiness = [0.05]

        #screen properties
        self.w = 0
        self.h = 0

        self.sceneFrameBuffer = []

    def updateScene(self, reset=False):
        if reset:
            self.initParametres()
        self.updateGL()

    #TODO:All this function will be changed to controll camera instance
    def set_zoom(self, diff):
        self.zoom += diff

    def get_zoom(self):
        return self.zoom

    def xRotation(self):
        return self.xRot

    def yRotation(self):
        return self.yRot

    def zRotation(self):
        return self.zRot

    def minimumSizeHint(self):
        return QtCore.QSize(50, 50)

    def sizeHint(self):
        return QtCore.QSize(400, 400)

    def set_x_rotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.xRot:
            self.xRot = angle
            self.emit(QtCore.SIGNAL("xRotationChanged(int)"), angle)
            self.updateGL()

    def set_y_rotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.yRot:
            self.yRot = angle
            self.emit(QtCore.SIGNAL("yRotationChanged(int)"), angle)
            self.updateGL()

    def set_z_rotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.zRot:
            self.zRot = angle
            self.emit(QtCore.SIGNAL("zRotationChanged(int)"), angle)
            self.updateGL()

    def TexFromPNG(self, filename):
        img = open(filename)
        img = img.rotate(180)
        img_data = numpy.array(list(img.getdata()), numpy.uint8)


        texture = glGenTextures(1)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        glBindTexture(GL_TEXTURE_2D, texture)

        # Texture parameters are part of the texture object, so you need to
        # specify them only once for a given texture object.
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.size[0], img.size[1], 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
        return texture

    def initializeGL(self):
        self.bed = self.makePrintingBed()
        self.axis = self.makeAxis()

        #load textures
        self.image_background = self.TexFromPNG("gui/background.png")

        glClearDepth(1.0)
        glShadeModel(GL_FLAT)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glCullFace(GL_FRONT_AND_BACK)

        #material
        glMaterialfv(GL_FRONT, GL_SPECULAR, self.materialSpecular)
        glMaterialfv(GL_FRONT, GL_SHININESS, self.materialShiness)

        #light
        glLightfv(GL_LIGHT0, GL_AMBIENT, self.lightAmbient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, self.lightDiffuse)
        glLightfv(GL_LIGHT0, GL_POSITION, self.lightPossition)
        glEnable(GL_LIGHT0)

        glColorMaterial ( GL_FRONT_AND_BACK, GL_EMISSION )
        glColorMaterial ( GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE )
        glBlendFunc(GL_SRC_ALPHA,GL_ONE)

        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_MULTISAMPLE)
        glEnable(GL_LINE_SMOOTH)
        #glEnable( GL_BLEND )




    def paintGL(self, selection = 1):
        if selection:
            glClearColor(0.0, 0.0, 0.0, 1.0)
            #glClearColor(1.0, 1.0, 1.0, 1.0)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()

            glTranslatef(0,-5,0)
            glTranslatef(0.0, 0.0, self.zoom)
            glRotated(-90.0, 1.0, 0.0, 0.0)
            glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
            glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)
            glLightfv(GL_LIGHT0, GL_POSITION, self.lightPossition)
            glDisable( GL_LIGHTING )
            glDisable( GL_LIGHT0 )
            glDisable( GL_BLEND )
            glEnable(GL_DEPTH_TEST)

            if self.parent.controller.scene.models:
                for model in self.parent.controller.scene.models:
                    self.draw_tool(model, self.parent.controller.settings, True)
                    model.render(picking=True, debug=False)

            glFlush()

            self.sceneFrameBuffer = self.grabFrameBuffer()
            self.sceneFrameBuffer.save("select_buffer.png")

            glEnable( GL_LIGHTING )
            glEnable( GL_LIGHT0 )

        glClearColor(0.0, 0.47, 0.62, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.draw_background_texture()
        glLoadIdentity()

        #self.draw_background_texture()

        glTranslatef(0,-5,0)
        glTranslatef(0.0, 0.0, self.zoom)
        glRotated(-90.0, 1.0, 0.0, 0.0)
        glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)
        glLightfv(GL_LIGHT0, GL_POSITION, self.lightPossition)

        glEnable( GL_BLEND )
        glCallList(self.bed)
        glDisable(GL_DEPTH_TEST)
        glCallList(self.axis)
        glDisable( GL_BLEND )

        #light
        glPointSize(5)
        glColor3f(0,1,1)
        glBegin(GL_POINTS)
        glVertex3fv(self.lightPossition[:3])
        glEnd()
        glEnable(GL_DEPTH_TEST)

        if 'debug' in self.parent.controller.settings:
            if self.parent.controller.settings['debug']:
                glBegin(GL_POINTS)
                glColor3f(1,0,0)
                glVertex3fv(self.parent.controller.scene.sceneZero)
                glEnd()

                glLineWidth(5)
                glBegin(GL_LINES)
                glColor3f(0,1,0)
                glVertex3fv(self.parent.controller.ray_start)
                glVertex3fv(self.parent.controller.ray_end)
                glEnd()

        '''
        draw scene with all objects
        '''
        glDisable( GL_BLEND )
        glEnable ( GL_LIGHTING )
        if self.parent.controller.scene.models:
            for model in self.parent.controller.scene.models:
                self.draw_tool(model, self.parent.controller.settings)
                model.render(picking=False, debug=self.parent.controller.settings['debug'] or False)

        glDisable( GL_LIGHTING )
        glEnable( GL_BLEND )

        glFlush()

    def draw_tool(self, model, settings, picking=False):
        if picking:
            rotateColors = [model.rotateColorXId, model.rotateColorYId, model.rotateColorZId]
            scaleColors = [model.scaleColorXId, model.scaleColorYId, model.scaleColorZId, model.scaleColorXYZId]
        else:
            rotateColors = [[255,0,0],[0,255,0],[0,0,255]]
            scaleColors = [[255,0,0],[0,255,0],[0,0,255], [255,255,255]]

        if settings['toolButtons']['rotateButton']:
            self.draw_rotation_circles(rotateColors, [i+o for i,o in zip(model.boundingSphereCenter, model.pos)], model.boundingSphereSize+0.1)
        elif settings['toolButtons']['scaleButton']:
            self.draw_scale_axes(scaleColors, [i+o for i,o in zip(model.boundingSphereCenter, model.pos)], model.boundingSphereSize+0.1)

    def draw_rotation_circles(self, colors, position, radius, picking=False):
        segments = 24
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])
        glColor3ubv(colors[0])
        glBegin(GL_LINE_LOOP)
        for i in xrange(0, 360, 360/segments):
            glVertex3f(math.cos(math.radians(i)) * radius, math.sin(math.radians(i)) * radius, 0.0)
        glEnd()
        glColor3ubv(colors[1])
        glBegin(GL_LINE_LOOP)
        for i in xrange(0, 360, 360/segments):
            glVertex3f(0., math.cos(math.radians(i)) * radius, math.sin(math.radians(i)) * radius)
        glEnd()
        glColor3ubv(colors[2])
        glBegin(GL_LINE_LOOP)
        for i in xrange(0, 360, 360/segments):
            glVertex3f(math.cos(math.radians(i)) * radius, 0., math.sin(math.radians(i)) * radius)
        glEnd()
        glPopMatrix()

    def draw_scale_axes(self, colors, position, radius, picking=False):
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])
        glColor3ubv(colors[0])
        glBegin(GL_LINES)
        glVertex3f(0., 0., 0.)
        glVertex3f(1.*radius, 0., 0.)
        glEnd()
        glColor3ubv(colors[1])
        glBegin(GL_LINES)
        glVertex3f(0., 0., 0.)
        glVertex3f(0., 1.*radius, 0.)
        glEnd()
        glColor3ubv(colors[2])
        glBegin(GL_LINES)
        glVertex3f(0., 0., 0.)
        glVertex3f(0., 0., 1.*radius)
        glEnd()
        glColor3ubv(colors[3])
        glBegin(GL_LINES)
        glVertex3f(0., 0., 0.)
        glVertex3f(1.*radius, 1.*radius, 1.*radius)
        glEnd()
        glPopMatrix()

    def resizeGL(self, width, height):
        self.w = width
        self.h = height
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, float(width*1./height*1.), 1, 1000)
        glMatrixMode(GL_MODELVIEW)

    def mousePressEvent(self, event):
        self.parent.controller.mouse_press_event(event)

    def mouseReleaseEvent(self, event):
        self.parent.controller.mouse_release_event(event)

    def mouseMoveEvent(self, event):
        self.parent.controller.mouse_move_event(event)

    def wheelEvent(self, event):
        logging.info('MouseWheel')
        self.parent.controller.wheel_event(event)

    def get_cursor_position(self, event):
        matModelView = glGetDoublev(GL_MODELVIEW_MATRIX )
        matProjection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv( GL_VIEWPORT )

        winX = event.x() * 1.0
        winY = viewport[3] - (event.y() *1.0)

        rayStart = gluUnProject(winX, winY, 0.0, matModelView, matProjection, viewport)
        rayEnd = gluUnProject(winX, winY, 1.0, matModelView, matProjection, viewport)

        return (rayStart, rayEnd)

    def get_cursor_pixel_color(self, event):
        color = []
        winX = event.x()
        winY = event.y()
        c = QColor(self.sceneFrameBuffer.pixel(winX, winY))
        color = [c.red(), c.green(), c.blue()]
        return color


    def makePrintingBed(self):
        genList = glGenLists(1)
        glNewList(genList, GL_COMPILE)

        glLineWidth(2)

        glBegin(GL_LINES)
        glColor3f(1,1,1)
        for i in xrange(-10, 11, 1):
            glVertex3d(i, 10, 0)
            glVertex3d(i, -10, 0)

            glVertex3d(10, i, 0)
            glVertex3d(-10, i, 0)

        glVertex3d(-10, 10, 0)
        glVertex3d(-10, 10, 20)

        glVertex3d(10, 10, 0)
        glVertex3d(10, 10, 20)

        glVertex3d(10, -10, 0)
        glVertex3d(10, -10, 20)

        glVertex3d(-10, -10, 0)
        glVertex3d(-10, -10, 20)

        glEnd()

        glBegin(GL_LINE_LOOP)

        glVertex3d(-10, 10, 20)
        glVertex3d(10, 10, 20)
        glVertex3d(10, -10, 20)
        glVertex3d(-10, -10, 20)

        glEnd()
        glEndList()

        return genList

    def makeAxis(self):
        genList = glGenLists(1)
        glNewList(genList, GL_COMPILE)

        glLineWidth(5)

        glBegin(GL_LINES)

        glColor3f(1, 0, 0)
        glVertex3d(-10, -10, 0)
        glVertex3d(-9, -10, 0)

        glColor3f(0, 1, 0)
        glVertex3d(-10, -10, 0)
        glVertex3d(-10, -9, 0)

        glColor3f(0, 0, 1)
        glVertex3d(-10, -10, 0)
        glVertex3d(-10, -10, 1)

        glEnd()
        glEndList()

        return genList

    def draw_background_texture(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        viewport = glGetIntegerv( GL_VIEWPORT )
        glOrtho(0.0, viewport[2], 0.0, viewport[3], -1.0, 1.0)
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
        glTexCoord2f(0, 0); glVertex3f(0, 0, 0)
        glTexCoord2f(0, 1); glVertex3f(0, viewport[3], 0)
        glTexCoord2f(1, 1); glVertex3f(viewport[2], viewport[3], 0)
        glTexCoord2f(1, 0); glVertex3f(viewport[2], 0, 0)
        glEnd()

        glEnable(GL_DEPTH_TEST)

        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)


    def normalizeAngle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle

    def normalizeAngleX(self, angle):
        if angle < 0:
            angle = 0
        if angle > 180:
            angle = 180
        return angle
