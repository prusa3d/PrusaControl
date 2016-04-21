# -*- coding: utf-8 -*-
import logging
from abc import ABCMeta, abstractmethod

import subprocess
from copy import deepcopy

from PyQt4.QtCore import QObject, QThread, pyqtSignal, SIGNAL, SLOT


class SlicerEngineAbstract():
    '''
    SlicerEngineAbstract is abstract class patern for others SlicerEngines
    '''
    __metaclass__ = ABCMeta

    @abstractmethod
    def slice(self):
        pass

    @abstractmethod
    def set_data(self, data):
        pass


class Slic3rEngineRunner(QObject):
    '''
    This is just connector to console version of Slic3r software
    first version
    '''
    step_increased = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self):
        super(Slic3rEngineRunner, self).__init__()
        self.slicer_place = '../Slic3r/bin/slic3r'
        self.data = {}

        self.step_max = 8
        self.step = 0

    def set_data(self, data):
        self.data = data

    def slice(self):
        process = subprocess.Popen([self.slicer_place,'tmp/tmp.stl','--output', 'tmp/out.gcode'], stdout=subprocess.PIPE)
        self.check_progress(process)
        self.finished.emit()

    def check_progress(self, process):
        for line in iter(process.stdout.readline, ''):
            self.step += 1
            if not line:
                break
            print(line.rstrip())
            self.step_increased.emit(int(((10. / 8.) * self.step) * 10))
            if self.step == 8:
                break

    def end(self):
        self.end_callback()



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


class SlicerEngineManager(object):
    '''
    SlicerEngineManager is class designed for managing slicers engine and prepare parameters
    '''
    def __init__(self, controller):
        self.controller = controller
        self.slice_thread = None
        self.slice_engine = None

    def slice(self):
        data = {'material': 'PLA',
                'quality': 'best',
                'scene': self.controller.scene
                }

        self.slice_thread = QThread()
        self.slice_engine = Slic3rEngineRunner()
        self.slice_engine.moveToThread(self.slice_thread)
        self.slice_engine.set_data(data)
        self.slice_thread.started.connect(self.slice_engine.slice)
        self.slice_engine.finished.connect(self.thread_ended)
        self.slice_engine.step_increased.connect(self.controller.set_progress_bar)

        self.slice_thread.start()

    def thread_ended(self):
        self.slice_thread.quit()
        self.controller.gcode_generated()
