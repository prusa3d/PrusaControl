#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import logging
import os
import platform
import tempfile
import sys
import urllib2

from ConfigParser import ConfigParser, RawConfigParser
from copy import deepcopy
from pprint import pprint

import errno
from shutil import copyfile, Error

import time

__author__ = 'Tibor Vavra'


#Mesure
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print('%s function took %0.3f ms' % (f.func_name, (time2-time1)*1000.0))
        return ret
    return wrap


class PrintingParameters(object):
    def __init__(self, app_config):
        self.application_parameters = app_config

        self.all_printers_parameters = {}
        self.all_materials_quality_parameters = {}

        self.printers_parameters = {}
        self.materials_quality_parameters = {}

        #read printers json file
        print(self.application_parameters.printers_parameters_file)
        self.all_printers_parameters = self.read_printers_parameters(self.application_parameters.printers_parameters_file)['printers']

        #apply default printer type settings
        #print("Printer type before: " + str(self.all_printers_parameters['default']['printer_type']))
        out = dict(self.apply_default_parameters(self.all_printers_parameters['default']['printer_type']))
        self.all_printers_parameters['default']['printer_type'] = out
        #apply default printer settings
        self.printers_parameters = self.apply_default_parameters(self.all_printers_parameters)

        #read all material configuration files for every printer
        for printer in self.get_printers_names():
            self.all_materials_quality_parameters[printer] = self.read_material_quality_parameters_for_printer(
                                                        self.application_parameters.user_folder + self.printers_parameters[printer]['material_parameters_file'])['materials']
        #apply default materials and default quality
        for printer in self.all_materials_quality_parameters:
            self.materials_quality_parameters[printer] = self.apply_default_material_parameters(
                                                        self.all_materials_quality_parameters[printer])

            #apply default material quality on other quality
            for material in self.materials_quality_parameters[printer]:
                self.materials_quality_parameters[printer][material]["quality"] = self.apply_default_quality_parameters(
                                                    self.materials_quality_parameters[printer][material]["quality"])

            #print("Material list without defaults quality: ")
            #pprint(self.materials_quality_parameters[printer])

            #merge printers dict with materials dict to one super list with all parameters
            self.printers_parameters[printer]['materials'] = self.materials_quality_parameters[printer]

            #print("Material list without default: ")
            #pprint(self.materials_quality_parameters[printer])


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

    def apply_default_material_parameters(self, dict_with_default):
        return_dict = {}
        for i in dict_with_default:
            if i == u'default':
                continue
            return_dict[i] = deepcopy(dict_with_default[u'default'])
            return_dict[i].update(dict_with_default[i])

            if u'quality' in dict_with_default[i]:
                return_dict[i][u'quality'] = deepcopy(dict_with_default[u'default'][u'quality'])
                return_dict[i][u'quality'].update(deepcopy(dict_with_default[i][u'quality']))
                if u'parameters' in return_dict[i][u'quality'][u'default']:
                    return_dict[i][u'quality'][u'default'][u'parameters'] = deepcopy(dict_with_default[u'default'][u'quality'][u'default'][u'parameters'])
                    return_dict[i][u'quality'][u'default'][u'parameters'].update(deepcopy(dict_with_default[i][u'quality'][u'default'][u'parameters']))

        return return_dict


    def apply_default_quality_parameters(self, dict_with_default):
        return_dict = {}
        for i in dict_with_default:
            if i == u'default':
                continue
            return_dict[i] = deepcopy(dict_with_default[u'default'])
            return_dict[i].update(dict_with_default[i])

            if u'parameters' in return_dict[i]:
                return_dict[i][u'parameters'] = deepcopy(dict_with_default[u'default'][u'parameters'])
                return_dict[i][u'parameters'].update(deepcopy(dict_with_default[i][u'parameters']))

        return return_dict

    def apply_default_parameters(self, dict_with_default):
        return_dict = {}
        for i in dict_with_default:
            updating_dict = {}
            if i == u'default':
                continue
            if 'parameters' in dict_with_default[i]:
                return_dict[i] = deepcopy(dict_with_default[u'default'])
                updating_dict = deepcopy(dict_with_default[i])
                del updating_dict['parameters']
                return_dict[i].update(updating_dict)
                return_dict[i]['parameters'].update(deepcopy(dict_with_default[i]['parameters']))
            else:
                return_dict[i] = deepcopy(dict_with_default[u'default'])
                return_dict[i].update(deepcopy(dict_with_default[i]))

        return return_dict


    def get_actual_settings(self, printer_name, printer_variation, material_name, quality_seting):
        if not printer_name or not printer_variation or not material_name or not quality_seting:
            return None
        else:
            if printer_name in self.printers_parameters:
                if printer_variation in self.printers_parameters[printer_name]["printer_type"]:
                    if material_name in self.printers_parameters[printer_name]["materials"]:
                        if quality_seting in self.printers_parameters[printer_name]["materials"][material_name]['quality']:
                            material_quality_pl = deepcopy(self.printers_parameters[printer_name]["materials"][material_name]['quality'][quality_seting]["parameters"])
                            final_pl = deepcopy(self.printers_parameters[printer_name]["parameters"])
                            printer_variation_pl = deepcopy(self.printers_parameters[printer_name]["printer_type"][printer_variation]['parameters'])
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

        self.is_version_actual = True

        self.config = ConfigParser()

        # read from version.txt
        try:
            with open("v.txt", 'r') as version_file:
                self.version_full = version_file.read()
                self.version = self.strip_version_string(self.version_full)
        except Exception:
            self.version_full = "0.1-1001"
            self.version = "0.1"

        self.json_settings_url = "https://raw.githubusercontent.com/prusa3d/PrusaControl-settings/master/"
        self.printers_filename = "printers.json"

        self.prusacontrol_url = "http://tbor.pythonanywhere.com/"
        self.prusacontrol_version_file = "prusacontrol_actual.info"


        if self.system_platform in ['Linux']:
            self.tmp_place = tempfile.gettempdir() + '/'
            self.data_folder = "data/"
            self.config_path = os.path.expanduser("~/.prusacontrol")
            self.user_folder = os.path.expanduser("~/.prusacontrol/")
            self.default_printers_parameters_file = os.path.expanduser(self.data_folder + self.printers_filename)
            self.printers_parameters_file = self.user_folder + self.printers_filename
            self.config.readfp(open('data/defaults.cfg'))
        elif self.system_platform in ['Darwin']:
            self.data_folder = "data/"
            self.tmp_place = tempfile.gettempdir() + '/'
            self.config_path = os.path.expanduser("~/.prusacontrol")
            self.user_folder = os.path.expanduser("~/.prusacontrol/")
            self.default_printers_parameters_file = os.path.expanduser(self.data_folder + self.printers_filename)
            self.printers_parameters_file = self.user_folder + self.printers_filename
            self.config.readfp(open('data/defaults.cfg'))
        elif self.system_platform in ['Windows']:
            self.data_folder = "data\\"
            self.tmp_place = tempfile.gettempdir() + '\\'

            self.config_path = os.path.expanduser("~\\prusacontrol.cfg")
            #self.user_folder = os.path.expanduser("~\\.prusacontrol\\")
            self.user_folder = self.tmp_place.split("\\appdata")[0] + "\\.prusacontrol\\"

            self.default_printers_parameters_file = os.path.expanduser(self.data_folder + self.printers_filename)
            self.printers_parameters_file = self.user_folder + self.printers_filename
            self.config.readfp(open('data\\defaults.cfg'))
            #print("Executable: " + sys.executable)
        else:
            self.data_folder = "data/"
            self.tmp_place = './'
            self.config_path = 'prusacontrol.cfg'
            self.user_folder = os.path.expanduser("~/.prusacontrol/")
            self.default_printers_parameters_file = os.path.expanduser(self.data_folder + self.printers_filename)
            self.printers_parameters_file = self.user_folder + self.printers_filename
            self.config.readfp(open('data/defaults.cfg'))

        self.config.read(self.config_path)

        self.first_run()

        #Check connections and update flag
        if self.internet_on() and self.config.getboolean('settings', 'automatic_update_parameters'):
            self.download_new_settings_files()
            self.check_versions()

            self.check_new_version_of_prusacontrol()




    def strip_version_string(self, string_in):
        string_out = string_in.split('-')
        string_out = string_out[:2]
        string_out = "_".join(string_out)[1:]
        return string_out

    def internet_on(self):
        try:
            urllib2.urlopen('http://google.com', timeout=1)
            return True
        except urllib2.URLError as err:
            return False

    def first_run(self):
        #check is there settings files in user folders
        printer_file_config = self.user_folder + self.printers_filename
        # if yes no first run
        if os.path.exists(printer_file_config):
            return
        # else copy from data folder to user folder
        else:
            try:
                os.makedirs(self.user_folder)
            except OSError as exception:
                if exception.errno != errno.EEXIST:
                    raise
            try:
                copyfile(self.data_folder + self.printers_filename, self.user_folder + self.printers_filename)
            except Error as e:
                logging.debug('Error: %s' % e)
            except IOError as e:
                logging.debug('Error: %s' % e.strerror)

            printers_data = json.load(open(self.user_folder + self.printers_filename, 'rb'))
            materials_files_list = [printers_data['printers'][i]['material_parameters_file'] for i in
                                    printers_data['printers'] if i not in ['default']]

            for i in materials_files_list:
                try:
                    copyfile(self.data_folder + i, self.user_folder + i)
                except Error as e:
                    logging.debug('Error: %s' % e)
                except IOError as e:
                    logging.debug('Error: %s' % e.strerror)


    #@timing
    def download_new_settings_files(self):
        printers_data = {}
        r = urllib2.urlopen(self.json_settings_url + self.printers_filename)
        with open(self.tmp_place+self.printers_filename, 'wb') as out_file:
            #shutil.copyfileobj(r, out_file)
            out_file.write(r.read())

        with open(self.tmp_place+self.printers_filename, 'r') as in_file:
            printers_data = json.load(in_file)
            materials_files_list = [printers_data['printers'][i]['material_parameters_file'] for i in
                                    printers_data['printers'] if i not in ['default']]

        if materials_files_list == []:
            logging.error("No internet connection or different network problem")
            return

        for i in materials_files_list:
            r = urllib2.urlopen(self.json_settings_url + i)
            with open(self.tmp_place+i, 'wb') as out_file:
                out_file.write(r.read())

    def check_versions(self):
        old = self.user_folder + self.printers_filename
        new = self.tmp_place + self.printers_filename
        #out = self.get_actual_version(old, new)

        res_old = self.get_printers_info(old)
        if res_old:
            old_version, old_material_list = res_old
        else:
            return

        res_new = self.get_printers_info(new)
        if res_new:
            new_version, new_material_list = res_new
        else:
            return

        if new_version > old_version:
            #print("nova verze printers-kopiruji")
            copyfile(new, self.user_folder + self.printers_filename)

        for i in new_material_list:
            new_material_version = self.get_materials_info(self.tmp_place + i)
            old_material_version = self.get_materials_info(self.user_folder+i)
            if new_material_version:
                if old_material_version:
                    if new_material_version > old_material_version:
                        copyfile(self.tmp_place + i, self.user_folder + i)

    def check_new_version_of_prusacontrol(self):
        #download json file with actual version
        r = urllib2.urlopen(self.prusacontrol_url + self.prusacontrol_version_file)
        data = r.read()
        if data:
            if self.is_higher(self.strip_version_string(data)):
                self.is_version_actual = False
            else:
                self.is_version_actual = True
        else:
            return None


    def get_printers_info(self, json_path):
        with open(json_path, 'r') as in_file:
            printers_data = json.load(in_file)
            materials_files_list = [printers_data['printers'][i]['material_parameters_file'] for i in
                                    printers_data['printers'] if i not in ['default']]

            version = printers_data['info']['version']
            return [version, materials_files_list]

        return None

    def get_materials_info(self, json_path):
        with open(json_path, 'r') as in_file:
            printers_data = json.load(in_file)
            return printers_data['info']['version']
        return None


    def is_higher(self, version_from_internet):
        splitted_version_from_internet = version_from_internet.split("_")
        splitted_local_version = self.version.split("_")

        print("Local version: " + str(splitted_local_version))
        print("Internet version: " + str(splitted_version_from_internet))

        version_from_internet_lst = splitted_version_from_internet[0].split(".")
        local_version_lst = splitted_local_version[0].split(".")

        if len(version_from_internet_lst) == len(local_version_lst):
            for i, o in zip(version_from_internet_lst, local_version_lst):
                if int(i) > int(o):
                    return True
            if int(splitted_version_from_internet[1]) > int(splitted_local_version[1]):
                return True
            else:
                return False
        else:
            return True

        return False




    def make_full_os_path(self, file):
        return os.path.expanduser(file)
