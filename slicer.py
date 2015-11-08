# -*- coding: utf-8 -*-

class SlicerEngineManager():
	'''
	SlicerEngineManager is class designed for managing slicers engine and prepare parameters
	'''
	pass


class SlicerEngineAbstract():
	'''
	SlicerEngineAbstract is abstract class patern for others SlicerEngines
	'''
	pass


class Slic3rEngine(SlicerEngineAbstract):
	'''
	This is just connector to console version of Slic3r software
	first version
	'''
	pass

class OwnSlicerEngine(SlicerEngineAbstract):
	'''
	PrusaResearch slicer engine, designed for their printers
	Future
	'''
	pass

