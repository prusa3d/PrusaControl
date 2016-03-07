#!/bin/bash

rm -rf build dist
pyinstaller --windowed --onefile /home/buildbot/projects/slave/buildbot-slave/Linux_All/build/main.py