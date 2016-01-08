# -*- coding: utf-8 -*-

from gui import PrusaControllView
from sceneData import AppScene, ModelTypeStl


class Controller:
    def __init__(self):
        self.view = PrusaControllView(self)
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
        self.view.statusBar().showMessage('Load file name: ' + data)
        self.model.model.append(ModelTypeStl().load(data))







    def openFile(self, urls):
        '''
        function for resolve whitch filetype will be loaded
        '''

        print(filename)
        pass



