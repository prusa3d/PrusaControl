#!/bin/bash

rm -rf build dist
pyinstaller -y --windowed --name=PrusaControl --onefile main.py --distpath ./dist/PrusaControl/
mkdir ./dist/PrusaControl/gui
cp gui/* dist/PrusaControl/gui/
mkdir ./dist/PrusaControl/translation
cp translation/* dist/PrusaControl/translation/