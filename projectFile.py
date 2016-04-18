import logging
from abc import ABCMeta, abstractmethod
from zipfile import ZipFile
import xml.etree.cElementTree as ET



class ProjectFile(object):

    def __init__(self, scene, filename=""):
        if filename:
            self.scene_xml = None
            self.scene = scene
            opened_zip = ZipFile(filename, 'r')
            for name in opened_zip.namelist():
                if name== "scene.xml":
                    self.scene_xml = opened_zip.read(name)
            if not self.scene_xml:
                logging.debug("Problem with reading %s, its not a standart PRUS file format." % filename)
                return False

            #TODO:check which version is scene.xml version and according to chose class to read project file
            self.version = Version_1_0()
            self.version.load(scene, filename)
        else:
            self.version = Version_1_0()
            self.scene = scene

    def save(self, filename):
        self.version.save(self.scene, filename)

class VersionAbstract(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def check_version(self, filename):
        return False

    @abstractmethod
    def get_version(self):
        return "Abstract version"

    @abstractmethod
    def load(self, scene, filename):
        logging.debug("This is abstract version class load function")
        return False

    @abstractmethod
    def save(self, scene, filename):
        logging.debug("This is abstract version class save function")
        return False


class Version_1_0(VersionAbstract):

    def check_version(self, filename):
        return True

    def get_version(self):
        return "1.0"

    def save(self, scene, filename):
        #create zipfile


        root = ET.Element("scene")
        version = ET.SubElement(root, "version").text=self.get_version()
        doc = ET.SubElement(root, "models")

        for model in scene.models:
            model_element = ET.SubElement(doc, "model", name=model.filename)
            normalization_element = ET.SubElement(model_element, "normalization").text=str(model.normalization_flag)
            position_element = ET.SubElement(model_element, "position").text=str(model.pos)
            rotation_element = ET.SubElement(model_element, "rotation").text=str(model.rot)
            scale_element = ET.SubElement(model_element, "scale").text=str(model.scale)

        tree = ET.ElementTree(root)
        tree.write(filename)

        return True

    def load(self, scene, filename):
        #open zipfile
        opened_zipfile = ZipFile(filename, 'r')
        #new_scene =


        tree = ET.parse(filename)
        version = tree.find('version')
        if self.get_version() == version:
            #clear scene
            scene.clearScene()
            #read models

        else:
            #problem
            return False
        models = tree.find('models')
        for model in models.findall('model'):
            pass





