# -*- coding: utf-8 -*-

from gui import PrusaControllView
from sceneData import AppScene, ModelTypeStl
from sceneRender import GLWidget


class Controller:
    def __init__(self):
        self.view = PrusaControllView(self)
        self.view.disableSaveGcodeButton()
        self.model = AppScene()

        self.settings = {}
        if not self.settings:
			self.settings['debug'] = False
			self.settings['language'] = 'en'
			self.settings['printer'] = 'prusa_i3_v2'

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

    def getView(self):
        return self.view

    def getModel(self):
        return self.model

    def openProjectFile(self):
        data = self.view.openProjectFileDialog()
        print(str(data))

    def saveProjectFile(self):
        data = self.view.saveProjectFileDialog()
        print(str(data))

    def saveGCodeFile(self):
        data = self.view.saveGCondeFileDialog()
        print(str(data))

    def openModelFile(self):
        data = self.view.openModelFileDialog()
        self.importModel(data)

    def importModel(self, path):
        self.view.statusBar().showMessage('Load file name: ' + path)
        self.model.models.append(ModelTypeStl().load(path))
        self.view.updateScene()

    def openSettings(self):
        self.settings = self.view.openSettingsDialog()
        print(str(self.settings))

    def generatePrint(self):
        self.view.enableSaveGcodeButton()

    def close(self):
        exit()

    def resetScene(self):
        self.model.clearScene()
        self.view.updateScene(True)

    def importImage(self, path):
        pass

    def openFile(self, url):
        '''
        function for resolve whitch filetype will be loaded
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





