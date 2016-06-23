#!/usr/bin/env python
# -*- coding: utf-8 -*-


__author__ = 'Tibor Vavra'


class Analyzer(object):
    def __init__(self):
        pass

    def make_analyze(self, scene):
        #Some initialization
        result = []
        support = {
            'name': 'Support',
            'result': False,
            'message': '',
            'gui_name': 'supportCheckBox'
        }
        if self.is_support_needed(scene):
            support['result'] = True
            support['message'] = "Some places in scene is hard to print without support. We are recommending to turn Support material parameter on"
        result.append(support)

        brim = {
            'name': 'Brim',
            'result': False,
            'message': '',
            'gui_name': 'brimCheckBox'
        }
        if self.is_brim_needed(scene):
            brim['result'] = True
            brim['message'] = "Contact area between printed object and printing surface is too small, it is possible that object will be detach during printing. We are recommending to turn Brim parametr on"
        result.append(brim)

        return result



    def is_support_needed(self, scene):
        #detect angles between normal vector of face and normal of printing surface
        #angel bigger than something is problem

        return True

    def is_brim_needed(self, scene):
        #detect small area on printing surface, it is need to generate brim
        return True






