<<<<<<< HEAD
# -*- coding: utf-8 -*-

=======
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import kivy
from ConfigParser import ConfigParser
import locale


__author__ = 'Tibor Vavra'

class Config():
	def __init__(self):
		self.languageFile = 'gui/language.data'
		self.guiFolder = 'gui'
		self.defaultLanguage = 'en_US'


class MultiLanguage(object):
	def __init__(self, config):
		#TODO: Placed in config file
        self.default = config.defaultLanguage
        self.language = self.getLanguage()
        self.languageFile = ConfigParser()
		self.languageFile.read(config.languageFile)


	def getLanguage(self):
        try:
            (a, _) = locale.getdefaultlocale()
        except Exception:
            kivy.Logger.warning(str(Exception))
            a = None
        if a:
            return a
        else:
            return self.default


    def getText(self, sid, localization=None):
        if not localization:
            localization = self.language

        if self.languageFile.has_section(localization):
            return self.getSaveText(localization, sid)
        else:
            return self.getSaveText(self.default, sid)

    def getSaveText(self, section, sid):
        try:
            value = self.languageFile.get(section, sid)
        except:
            kivy.Logger.warning(str(Exception))
            return '!!!' + sid + '!!!'
        return value

    def setLanguage(self, lang):
        self.language = lang
>>>>>>> a007b1d5576f357a833085e3871ee58a3a0bcce1
