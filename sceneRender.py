# -*- coding: utf-8 -*-

from kivy.uix.floatlayout import FloatLayout


class PrusaControllWidget(FloatLayout):
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


class Scene(object):
	'''
	Scene is class representing data from AppScene, it is simplificated data of scene, rendering is less important then printing
	'''
	pass
