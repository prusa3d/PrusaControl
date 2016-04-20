# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod


class SlicerEngineManager(object):
    '''
    SlicerEngineManager is class designed for managing slicers engine and prepare parameters
    '''
    def __init__(self, controller, slice_engine=Slic3rEngine()):
        self.controller = controller
        self.slice_engine = slice_engine

    def slice(self):
        data = {'material': 'PLA',
                'quality': 'best',
                'scene': self.controller.scene
                }

        self.slice_engine.slice(data)


class SlicerEngineAbstract(object):
    '''
    SlicerEngineAbstract is abstract class patern for others SlicerEngines
    '''
    __metaclass__ = ABCMeta

    @abstractmethod
    def slice(self, data):
        pass



class Slic3rEngine(SlicerEngineAbstract):
    '''
    This is just connector to console version of Slic3r software
    first version
    '''
    def slice(self, data):
        pass



class CuraEngine(SlicerEngineAbstract):
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

