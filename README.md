# PrusaControl is deprecated

PrusaControl is an alternative user interface for Slic3r Prusa Edition. With focus to be easy to use, novice friendly, multi-language and with auto updated printing settings. Just load stl file, select material and press generate button.

#### Key features
- Simple and good looking user interface
- Best from Slic3r slicing engine
- Multi-language
- For main desktop platforms (Windows, macOS, Linux)
- Auto-updated printing settings
- Software update check
- Easy use rotation and scale tool
- Undo and Redo

Some features are still in development

Video:
[![](http://img.youtube.com/vi/YYqVhhM7XIc/0.jpg)](http://www.youtube.com/watch?v=YYqVhhM7XIc "")


### Dependencies (tested version)

- python (3.5.x)
- PyQt4 (4.11.4)
- numpy (1.12.1)
- numpy-stl (2.2.3)
- pyrr (0.8.3)
- PyOpenGL (3.1.0)
- PyOpenGL-accelerate (3.1.0)
- Slic3r PE (>=1.31.2)

- pyobjc (3.2.1) on macOS platform

Slic3r is placed in folder tools/Slic3r-Lite

### Documentation
Not yet, but we are working on it :-)

### Translations
If you want to create translation of PrusaControl, to your native language, you can. First, check if your language is not in folder **ts** or in **pull request** section. If you find pull request, of your language, please review it. We are not able to check every language and we will accept only translations reviewed by some other translator.

For translating to new language, make **fork** of PrusaControl repository. Create new file in **ts** folder by copy/rename of file **en_US.ts** and use it as example. Its XML file with simple structure. Please, try to make same long strings as in English translation and be careful on space/tab symbols. You can use tool Qt Linguist for edit and generating binary version .qm of translation. For testing, you have to add binary (.qm) file to translation folder and add new language identifier to controller.py file in dict self.enumeration(around line 92). **When you are done, create pull request only from new .ts file.**


### License
PrusaControl is licensed under GPLv3
