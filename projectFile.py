import ast
import logging
from abc import ABCMeta, abstractmethod
from zipfile import ZipFile
import xml.etree.cElementTree as ET

import io
from stl.mesh import Mesh

from sceneData import ModelTypeStl


class ProjectFile(object):

    def __init__(self, scene, filename=""):
        if filename:
            self.scene_xml = None
            self.scene = scene

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

    def load(self, scene, filename):
        #open zipfile
        with ZipFile(filename, 'r') as opened_zipfile:
            tree = ET.fromstring(opened_zipfile.read('scene.xml'))
            version = tree.find('version').text
            if self.get_version() == version:
                logging.debug("Ano, soubor je stejna verze jako knihovna pro jeho nacitani. Pokracujeme")
            else:
                logging.debug("Problem, tuto verzi neumim nacitat.")
                return False
            models = tree.find('models')
            models_data = []
            for model in models.findall('model'):
                model_data = {}
                model_data['file_name'] = model.get('name')
                model_data['normalization'] = ast.literal_eval(model.find('normalization').text)
                model_data['position'] = ast.literal_eval(model.find('position').text)
                model_data['rotation'] = ast.literal_eval(model.find('rotation').text)
                model_data['scale'] = ast.literal_eval(model.find('scale').text)
                models_data.append(model_data)

            logging.debug(str(models_data))

            scene.models = []
            for m in models_data:
                logging.debug("Jmeno souboru je: " + m['file_name'])
                model = ModelTypeStl.load_from_mesh(Mesh.from_file(filename="", fh=opened_zipfile.open(m['file_name']), m['file_name']), normalize=not m['normalize'])
                model.rot = m['rotation']
                model.pos = m['position']
                model.scale = m['scale']

                scene.models.append(model)

    def save(self, scene, filename):
        #create zipfile
        with ZipFile(filename, 'w') as opened_zipfile:
            root = ET.Element("scene")
            version = ET.SubElement(root, "version").text=self.get_version()
            models_tag = ET.SubElement(root, "models")

            for model in scene.models:
                model_element = ET.SubElement(models_tag, "model", name=model.filename)
                normalization_element = ET.SubElement(model_element, "normalization").text=str(model.normalization_flag)
                position_element = ET.SubElement(model_element, "position").text=str(model.pos)
                rotation_element = ET.SubElement(model_element, "rotation").text=str(model.rot)
                scale_element = ET.SubElement(model_element, "scale").text=str(model.scale)

            tree = ET.ElementTree(root)
            tree.write(filename)






        return True




