# -*- coding: utf-8 -*-
import logging

import sceneData
from gui import PrusaControllView
from sceneData import AppScene, ModelTypeStl
from sceneRender import GLWidget

from PyQt4 import QtCore


class Controller:
    def __init__(self):
        logging.info('Controller instance created')
        self.view = PrusaControllView(self)
        self.view.disableSaveGcodeButton()
        self.scene = AppScene()

        #TODO:Reading settings from file
        self.settings = {}
        if not self.settings:
            self.settings['debug'] = False
            self.settings['language'] = 'en'
            self.settings['printer'] = 'prusa_i3_v2'
            self.settings['toolButtons'] = {
                'moveButton': False,
                'rotateButton': False,
                'scaleButton': False
            }

        self.printingSettings = {
            'materials': ['ABS', 'PLA', 'FLEX'],
        }


        #TODO:Add extra file for printing settings(rules)
        self.enumeration = {
            'language': {
                'cs': 'Czech',
                'en': 'English'
            },
            'printer': {
                'prusa_i3': 'Prusa i3',
                'prusa_i3_v2': 'Prusa i3 v2'
            }
        }

        #variables for help
        self.last_pos = QtCore.QPoint()
        self.ray_start = [.0, .0, .0]
        self.ray_end = [.0, .0, .0]
        self.res_old = []

    def getView(self):
        return self.view

    def getModel(self):
        return self.scene

    def openProjectFile(self):
        data = self.view.openProjectFileDialog()
        logging.debug('open project file %s' %data)

    def saveProjectFile(self):
        data = self.view.saveProjectFileDialog()
        logging.debug('save project file %s' %data)

    def saveGCodeFile(self):
        data = self.view.saveGCondeFileDialog()
        print(str(data))

    def openModelFile(self):
        data = self.view.openModelFileDialog()
        logging.debug('open model file %s' %data)
        self.importModel(data)

    def importModel(self, path):
        self.view.statusBar().showMessage('Load file name: ' + path)
        self.scene.models.append(ModelTypeStl().load(path))
        self.view.updateScene()

    def openSettings(self):
        self.settings = self.view.openSettingsDialog()
        print(str(self.settings))

    def generatePrint(self):
        self.view.enableSaveGcodeButton()

    def close(self):
        exit()

    def wheel_event(self, event):
        logging.debug('MouseWheel')
        self.view.set_zoom(event.delta()/120)
        self.view.statusBar().showMessage("Zoom = %s" % self.view.get_zoom())
        self.view.updateScene()

    def mouse_press_event(self, event):
        logging.debug('Tlacitko mysi bylo stisknuto')
        self.last_pos = QtCore.QPoint(event.pos())
        if event.buttons() & QtCore.Qt.LeftButton & (self.settings['toolButtons']['moveButton'] or self.settings['toolButtons']['rotateButton'] or self.settings['toolButtons']['scaleButton']):
            newRayStart, newRayEnd = self.view.get_cursor_position(event)
            self.res_old = sceneData.intersectionRayPlane(newRayStart, newRayEnd)
            self.hit_objects(event)
            self.view.updateScene()

    def mouse_release_event(self, event):
        logging.debug('Tlacitko mysi bylo uvolneno')
        logging.debug('Odoznacit vsechny objekty ve scene')
        for model in self.scene.models:
            model.selected = False
        self.view.updateScene()

    def mouse_move_event(self, event):
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()

        if event.buttons() & QtCore.Qt.LeftButton & self.settings['toolButtons']['moveButton']:
            logging.debug('Mouse move event spolu s levym tlacitkem a je nastaveno Move tool')
            newRayStart, newRayEnd = self.view.get_cursor_position(event)
            res = sceneData.intersectionRayPlane(newRayStart, newRayEnd)
            if res is not None:
                res_new = sceneData.Vector.minusAB(res, self.res_old)
                for model in self.scene.models:
                    if model.selected:
                        model.pos = [p+n for p, n in zip(model.pos, res_new)]
                    self.res_old = res

            #self.oldPos3d = newVector

        elif event.buttons() & QtCore.Qt.LeftButton & self.settings['toolButtons']['rotateButton']:
            #TODO:Dodelat rotaci
            logging.debug('Mouse move event spolu s levym tlacitkem a je nastaveno Rotate tool')

        elif event.buttons() & QtCore.Qt.LeftButton & self.settings['toolButtons']['scaleButton']:
            #TODO:Dodelat scale
            logging.debug('Mouse move event spolu s levym tlacitkem a je nastaveno Scale tool')

        elif event.buttons() & QtCore.Qt.RightButton:
            #TODO:Add controll of camera instance
            self.view.set_x_rotation(self.view.get_x_rotation() + 8 * dy)
            self.view.set_z_rotation(self.view.get_z_rotation() + 8 * dx)

        self.last_pos = QtCore.QPoint(event.pos())
        self.view.updateScene()

    def hit_objects(self, event):
        possible_hit = []

        self.ray_start, self.ray_end = self.view.get_cursor_position(event)

        for model in self.scene.models:
            if model.intersectionRayBoundingSphere(self.ray_start, self.ray_end):
                possible_hit.append(model)
            else:
                model.selected = False

        for model in possible_hit:
            if model.intersectionRayModel(self.ray_start, self.ray_end):
                model.selected = not model.selected
            else:
                model.selected = False

        return False


    def resetScene(self):
        self.scene.clearScene()
        self.view.updateScene(True)

    def importImage(self, path):
        pass

    def moveButtonPressed(self):
        print('Move button pressed')
        self.clearToolButtonStates()
        self.settings['toolButtons']['moveButton'] = True

    def rotateButtonPressed(self):
        print('Rotate button pressed')
        self.clearToolButtonStates()
        self.settings['toolButtons']['rotateButton'] = True

    def scaleButtonPressed(self):
        print('Scale button pressed')
        self.clearToolButtonStates()
        self.settings['toolButtons']['scaleButton'] = True
        print(str(self.settings))

    def clearToolButtonStates(self):
        self.settings['toolButtons'] = {a: False for a in self.settings['toolButtons']}


    def openFile(self, url):
        '''
        function for resolve which file type will be loaded
        '''
        #self.view.statusBar().showMessage('Load file name: ')

        urlSplited = url.split('.')
        if len(urlSplited)>1:
            fileEnd = urlSplited[1]
        else:
            fileEnd=''

        if fileEnd in ['stl', 'STL', 'Stl']:
            print('import model')
            self.importModel(url)
        elif fileEnd in ['prus']:
            print('open project')
            self.openProjectFile(url)
        elif fileEnd in ['jpeg', 'jpg', 'png', 'bmp']:
            print('import image')
            self.importImage(url)





