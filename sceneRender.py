# -*- coding: utf-8 -*-
import logging
from OpenGL.GL import *
from OpenGL.GLU import *


from PyQt4.QtOpenGL import *
from PyQt4 import QtCore


class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        QGLWidget.__init__(self, parent)

        self.parent = parent
        self.initParametres()

    def initParametres(self):
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


    def updateScene(self, reset=False):
        if reset:
            self.initParametres()
        self.updateGL()

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

    def initializeGL(self):
        self.bed = self.makePrintingBed()
        self.axis = self.makeAxis()

        glClearDepth(1.0)
        glShadeModel(GL_FLAT)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

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
        glBlendFunc( GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA )

        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_MULTISAMPLE)
        glEnable(GL_LINE_SMOOTH)
        glEnable( GL_BLEND )

        glEnable(GL_CULL_FACE)


    def paintGL(self):
        glClearColor(0.0, 0.47, 0.62, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslated(0,-5,0)
        glTranslated(0.0, 0.0, self.zoom)
        glRotated(-90.0, 1.0, 0.0, 0.0)
        glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)
        glLightfv(GL_LIGHT0, GL_POSITION, self.lightPossition)

        glCallList(self.bed)
        glDisable(GL_DEPTH_TEST)
        glCallList(self.axis)

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
                model.render(self.parent.controller.settings['debug'] or False)

        glDisable( GL_LIGHTING )
        glEnable( GL_BLEND )

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        #TODO:Fix perspective correction, wrong calculation now, deformated view
        gluPerspective(60*((width*1.0)/(height*1.0)), (width*1.0)/(height*1.0), 0.0001, 1000.0)
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
