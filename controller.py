# -*- coding: utf-8 -*-

from gui import PrusaControllView
from sceneData import AppScene, ModelTypeStl
from sceneRender import GLWidget


class Controller:
    def __init__(self):
        self.view = PrusaControllView(self)
        self.view.disableSaveGcodeButton()
        self.model = AppScene()

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
        modelData = ModelTypeStl().load(path)
        self.model.modelsData.append(modelData)
        self.model.models.append(modelData.makeDisplayList())
        self.view.updateScene()

    def openSettings(self):
        data = self.view.openSettingsDialog()

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

        if fileEnd in ['stl']:
            print('import model')
            self.importModel(url)
        elif fileEnd in ['prus']:
            print('open project')
            self.openProjectFile(url)
        elif fileEnd in ['jpeg', 'jpg', 'png', 'bmp']:
            print('import image')
            self.importImage(url)





