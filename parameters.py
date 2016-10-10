#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import platform
import tempfile

from ConfigParser import ConfigParser, RawConfigParser
from copy import deepcopy
from pprint import pprint

__author__ = 'Tibor Vavra'



class PrintingParameters(object):
    def __init__(self, app_config):
        self.application_parameters = app_config

        self.all_printers_parameters = {}
        self.all_materials_quality_parameters = {}

        self.printers_parameters = {}
        self.materials_quality_parameters = {}

        #read printers json file
        self.all_printers_parameters = self.read_printers_parameters(self.application_parameters.printers_parameters_file)

        #apply default printer type settings
        self.all_printers_parameters['default']['printer_type'] = self.apply_default_parameters(self.all_printers_parameters['default']['printer_type'])
        #apply default printer settings
        self.printers_parameters = self.apply_default_parameters(self.all_printers_parameters)

        #read all material configuration files for every printer
        for printer in self.get_printers_names():
            self.all_materials_quality_parameters[printer] = self.read_material_quality_parameters_for_printer(
                                                        self.printers_parameters[printer]['material_parameters_file'])
        #apply default materials and default quality
        for printer in self.all_materials_quality_parameters:
            self.materials_quality_parameters[printer] = self.apply_default_parameters(
                                                        self.all_materials_quality_parameters[printer])

            for material in self.materials_quality_parameters[printer]:
                self.materials_quality_parameters[printer][material]["quality"] = self.apply_default_parameters(
                                                    self.all_materials_quality_parameters[printer][material]["quality"])

            #merge printers dict with materials dict to one super list with all parameters
            self.printers_parameters[printer]['materials'] = self.materials_quality_parameters[printer]



    def get_printers_names(self):
        return self.printers_parameters.keys()

    def get_printers_parameters(self):
        return self.printers_parameters

    def get_printer_parameters(self, printer_name):
        if printer_name in self.printers_parameters.keys():
            return self.printers_parameters[printer_name]
        else:
            return None

    def get_materials_for_printer(self, printer_name):
        if printer_name in self.materials_quality_parameters.keys():
            return self.materials_quality_parameters[printer_name]
        else:
            return []

    def get_materials_quality_for_printer(self, printer_name, material):
        if printer_name in self.printers_parameters and material in self.printers_parameters[printer_name]["materials"]:
            return self.printers_parameters[printer_name]["materials"][material]
        else:
            return []

    def apply_default_parameters(self, dict_with_default):
        return_dict = {}
        for i in dict_with_default.keys():
            if i == u'default':
                continue
            if 'parameters' in dict_with_default[i].keys():
                return_dict[i] = dict(dict_with_default[u'default'])
                updating_dict = dict(dict_with_default[i])
                del updating_dict['parameters']
                return_dict[i].update(updating_dict)
                return_dict[i]['parameters'].update(dict_with_default[i]['parameters'])
            else:
                return_dict[i] = dict(dict_with_default[u'default'])
                return_dict[i].update(dict_with_default[i])

        return return_dict


    def get_actual_settings(self, printer_name, printer_variation, material_name, quality_seting):
        print("Option: " + str(printer_name) + ' ' + str(printer_variation) + ' ' + str(material_name) + ' ' + str(quality_seting))
        if not printer_name or not printer_variation or not material_name or not quality_seting:
            return None
        else:
            if printer_name in self.printers_parameters:
                if printer_variation in self.printers_parameters[printer_name]["printer_type"]:
                    if material_name in self.printers_parameters[printer_name]["materials"]:
                        if quality_seting in self.printers_parameters[printer_name]["materials"][material_name]['quality']:
                            material_quality_pl = dict(self.printers_parameters[printer_name]["materials"][material_name]['quality'][quality_seting]["parameters"])
                            final_pl = dict(self.printers_parameters[printer_name]["parameters"])
                            printer_variation_pl = dict(self.printers_parameters[printer_name]["printer_type"][printer_variation]['parameters'])
                            final_pl.update(material_quality_pl)
                            final_pl.update(printer_variation_pl)
                            return final_pl
                        else:
                            return None
                    else:
                        return None
                else:
                    return None
            else:
                return None
        return None

    def read_printers_parameters(self, filename):
        printers = {}
        with open(filename, 'rb') as json_file:
            printers = json.load(json_file)
        return printers



    def read_material_quality_parameters_for_printer(self, printer_config_file):
        if not printer_config_file:
            return None

        material_config = []
        with open(printer_config_file, 'rb') as json_file:
            material_config = json.load(json_file)

        return material_config




class AppParameters(object):
    def __init__(self, controller=None, local_path=''):
        self.local_path = local_path
        self.controller = controller
        self.system_platform = platform.system()

        self.config = ConfigParser()

        if self.system_platform in ['Linux']:
            self.tmp_place = tempfile.gettempdir() + '/'
            self.config_path = os.path.expanduser("~/.prusacontrol")
            self.printing_parameters_file = os.path.expanduser("data/printing_parameters.json")
            self.printers_parameters_file = os.path.expanduser("data/printers.json")
            self.config.readfp(open('data/defaults.cfg'))
        elif self.system_platform in ['Darwin']:
            self.tmp_place = tempfile.gettempdir() + '/'
            self.config_path = os.path.expanduser("~/.prusacontrol")
            self.printing_parameters_file = os.path.expanduser("data/printing_parameters.json")
            self.printers_parameters_file = os.path.expanduser("data/printers.json")
            self.config.readfp(open('data/defaults.cfg'))
        elif self.system_platform in ['Windows']:
            self.tmp_place = tempfile.gettempdir() + '\\'
            self.config_path = os.path.expanduser("~\\prusacontrol.cfg")
            self.printing_parameters_file = os.path.expanduser("data\\printing_parameters.json")
            self.printers_parameters_file = os.path.expanduser("data\\printers.json")
            self.config.readfp(open('data\\defaults.cfg'))
        else:
            self.tmp_place = './'
            self.config_path = 'prusacontrol.cfg'
            self.printing_parameters_file = "data/printing_parameters.json"
            self.printers_parameters_file = os.path.expanduser("data/printers.json")
            self.config.readfp(open('data/defaults.cfg'))

        self.config.read(self.config_path)

        #read from version.txt
        try:
            with open("v.txt", 'r') as version_file:
                self.version_full = version_file.read()
                self.version = self.version_full.split('-')
                self.version = self.version[:2]
                self.version = "_".join(self.version)[1:]
        except Exception:
            self.version_full = "0.1-1001"
            self.version = "0.1"


    def make_full_os_path(self, file):
        return os.path.expanduser(file)
