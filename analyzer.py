#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
from PyQt4.QtCore import QObject
from PyQt4.QtCore import QThread
from PyQt4.QtCore import pyqtSignal

__author__ = 'Tibor Vavra'


class Analyzer(object):
    def __init__(self, controller):
        self.controller = controller
        self.analyzer_runner = AnalyzerRunner(controller)
        self.analyzer_runner_thread = QThread()

    def make_analyze_in_thread(self, whole_scene):
        self.analyzer_runner.moveToThread(self.analyzer_runner_thread)
        self.analyzer_runner_thread.started.connect(self.analyzer_runner.start_analyze)

        self.analyzer_runner.finished.connect(self.set_finished_read)
        self.analyzer_runner.send_result.connect(self.set_result)


    def cancel_analyz(self):
        self.analyzer_runner.is_running = False
        self.gcode_parser_thread.quit()
        self.gcode_parser_thread.wait()

    def set_finished_read(self):
        print("analyze done")

    def set_result(self, result):
        pass



    '''
    def make_analyze(self, whole_scene):
        #Some initialization
        result = []
        support = {
            'name': 'Support',
            'result': False,
            'message': '',
            'gui_name': 'supportCheckBox'
        }
        if self.is_support_needed(whole_scene):
            support['result'] = True
            support['message'] = "Some places in scene is hard to print without support. We are recommending to turn Support material parameter on"
        result.append(support)

        brim = {
            'name': 'Brim',
            'result': False,
            'message': '',
            'gui_name': 'brimCheckBox'
        }
        if self.is_brim_needed(whole_scene):
            brim['result'] = True
            brim['message'] = "Contact area between printed object and printing surface is too small, it is possible that object will be detach during printing. We are recommending to turn Brim parametr on"
        result.append(brim)

        return result



    def is_support_needed(self, scene):
        #detect angles between normal vector of face and normal of printing surface
        #angel bigger than something is problem
        data = self.controller.scene.get_faces_by_smaller_angel_normal_and_vector(np.array([0.,0.,-1.]), 35., scene)
        #something returned? problematic printing without support, recommended to turn it on
        if len(data) == 0:
            return False
        else:
            return True

        return True

    def is_brim_needed(self, scene):
        #detect small area on printing surface, it is need to generate brim
        #something returned? problematic printing without brim, recommended to turn it on
        return self.controller.scene.get_contact_faces_with_area_smaller_than(2., scene)
    '''


class AnalyzerRunner(QObject):
    finished = pyqtSignal()
    send_result = pyqtSignal(dict)

    def __init__(self, controller, whole_scene = None):
        super(AnalyzerRunner, self).__init__()
        self.is_running = True
        self.controller = controller
        self.whole_scene = whole_scene

    def start_analyze(self):
        result = {}
        if self.is_running:
            if self.is_support_needed(self.whole_scene):
                result['support'] = True
            else:
                result['support'] = False
        if self.is_running:
            if self.is_brim_needed(self.whole_scene):
                result['brim'] = True
            else:
                result['brim'] = False
        self.send_result.emit(result)

        self.finished.emit()







