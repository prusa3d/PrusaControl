#!/usr/bin/env python
# -*- coding: utf-8 -*-

import vcversioner

version = vcversioner.find_version(root='.', version_file='%(root)s/data/v.txt').version
version_lst = version.split('.')
major_version = int(version_lst[0])
minor_version = int(version_lst[1])
bugfix_version = int(version_lst[2])
build_version = int(version_lst[3][4:])

#print("Splitted: " + str(major_version) + ' ' + str(minor_version) + ' ' + str(bugfix_version) + ' ' + str(build_version))

version_string_uni = u'%i, %i, %i, %i' % (major_version, minor_version, bugfix_version, build_version)
version_string = "(%i, %i, %i, %i)" % (major_version, minor_version, bugfix_version, build_version)
print(version_string)


with open("version.txt", "w") as version_file:
    version_file.write("VSVersionInfo(\n")
    version_file.write("  ffi=FixedFileInfo(\n")
    version_file.write("    filevers="+ version_string+',\n')
    version_file.write("    prodvers="+ version_string+',\n')
    version_file.write("    mask=0x3f,\n")
    version_file.write("    flags=0x0,\n")
    version_file.write("    OS=0x4,\n")
    version_file.write("    fileType=0x1,\n")
    version_file.write("    subtype=0x0,\n")
    version_file.write("    date=(0, 0)\n")
    version_file.write("    ),\n")
    version_file.write("  kids=[\n")
    version_file.write("    StringFileInfo(\n")
    version_file.write("      [\n")
    version_file.write("      StringTable(\n")
    version_file.write("        u'040904b0',\n")
    version_file.write("        [StringStruct(u'CompanyName', u'Prusa Research, s.r.o.'),\n")
    version_file.write("        StringStruct(u'ProductName', u'PrusaControl'),\n")
    version_file.write("        StringStruct(u'ProductVersion', u'"+version_string_uni+"'),\n")
    version_file.write("        StringStruct(u'InternalName', u'PrusaControl'),\n")
    version_file.write("        StringStruct(u'OriginalFilename', u'PrusaControl.exe'),\n")
    version_file.write("        StringStruct(u'FileVersion', u'"+version_string_uni+"'),\n")
    version_file.write("        StringStruct(u'FileDescription', u'PrusaControl'),\n")
    version_file.write("        StringStruct(u'LegalCopyright', u'Copyright 2017 Prusa Research s.r.o.'),\n")
    version_file.write("        StringStruct(u'LegalTrademarks', u''),])\n")
    version_file.write("      ]),\n")
    version_file.write("    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])\n")
    version_file.write("  ]\n")
    version_file.write(")\n")






