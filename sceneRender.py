# -*- coding: utf-8 -*-
import kivy
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.context_instructions import *
from kivy.graphics.context_instructions import UpdateNormalMatrix
from kivy.graphics.instructions import *
from kivy.graphics.opengl import *
from kivy.graphics.transformation import *
from kivy.graphics.vertex_instructions import Mesh
from kivy.resources import resource_find
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.properties import *

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from objloader import ObjFile


class PrusaControllWidget(Widget):
	'''
	Main widget of application
	'''
	pass


class CenteredCamera(object):
	'''
	Special camera class, this camera is centered on scene and rotate around
	it can zoom in and out
	hanndle mouse events
	'''
	pass


class SceneRenderer(CenteredCamera):
	'''
	Scene Renderer widget, renderer designed for drawing a Scene data
	'''
	pass



class RendererBasic(Widget):
    def __init__(self, **kwargs):
        self.pressed = False
        self.newCursorPos = self.oldCursorPos = {'x': 0, 'y': 0}
        self.rotation = 0
        self.canvas = RenderContext(compute_normal_mat=True)
        self.canvas.shader.source = resource_find('simple.glsl')
        self.scene = ObjFile(resource_find("monkey.obj"))
        super(RendererBasic, self).__init__(**kwargs)
        with self.canvas:
            self.cb = Callback(self.setup_gl_context)
            PushMatrix()
            self.setup_scene()
            PopMatrix()
            self.cb = Callback(self.reset_gl_context)
        Clock.schedule_interval(self.update_glsl, 1 / 60.)

    def setup_gl_context(self, *args):
        glEnable(GL_DEPTH_TEST)

    def reset_gl_context(self, *args):
        glDisable(GL_DEPTH_TEST)

    def update_glsl(self, *largs):
        Window.clearcolor = (0.75, 0.75, 0.75, 1)
        asp = self.width / float(self.height)
        proj = Matrix().view_clip(-asp, asp, -1, 1, 1, 100, 1)
        self.canvas['projection_mat'] = proj
        self.canvas['diffuse_light'] = (1.0, 1.0, 0.8)
        self.canvas['ambient_light'] = (0.1, 0.1, 0.1)
        #self.rot.angle += 1
        #kivy.Logger.info('%s' % type(self.rot))
        #self.rot.x += self.newCursorPos['x']
        #self.rot.y += self.newCursorPos['y']

        if self.pressed:
            self.rot_cam_x.angle = (self.newCursorPos['x']) * 50
            self.rot_cam_y.angle = (self.newCursorPos['y']) * 50

        #kivy.Logger.info('rotace v %s x %s' % (self.newCursorPos['x'], self.newCursorPos['y']))


    def setup_scene(self):
        Color(1, 1, 1, 1)
        PushMatrix()
        Translate(0, 0, -3)
        self.rot_cam_x = Rotate(1, 0, 1, 0)
        self.rot_cam_y = Rotate(1, -1, 0, 0)


        m = list(self.scene.objects.values())[0]
        UpdateNormalMatrix()
        self.mesh = Mesh(
            vertices=m.vertices,
            indices=m.indices,
            fmt=m.vertex_format,
            mode='triangles',
        )
        PopMatrix()

    def on_touch_move(self, touch):

        #kivy.Logger.info('%s' % str(touch.spos[0]))

        #self.newCursorPos['x'] = ((touch.spos[0] -.5) - self.oldCursorPos['x'])
        #self.newCursorPos['y'] = ((touch.spos[1] -.5) - self.oldCursorPos['y'])

        self.newCursorPos['x'] = (touch.spos[0] -.5)
        self.newCursorPos['y'] = (touch.spos[1] -.5)

        kivy.Logger.info('Vektor noveho pohybu je v %s x %s' % (self.newCursorPos['x'], self.newCursorPos['y']))

        #self.oldCursorPos['x'] = touch.spos[0]
        #self.oldCursorPos['y'] = touch.spos[1]


    def on_touch_down(self, touch):
        self.pressed = True
        self.oldCursorPos['x'] = touch.spos[0] - .5
        self.oldCursorPos['y'] = touch.spos[1] - .5

        kivy.Logger.info('stisknuto tlacitko mysi %s x %s' % (touch.x, touch.y))

    def on_touch_up(self, touch):
        self.pressed = False
        kivy.Logger.info('pusteno tlacitko mysi %s x %s' % (touch.x, touch.y))

        self.oldCursorPos['x'] = 0
        self.oldCursorPos['y'] = 0



class Scene(object):
	'''
	Scene is class representing data from AppScene, it is simplificated data of scene, rendering is less important then printing
	'''
	pass
