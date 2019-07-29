#!/bin/bash 
set -x
filename=InteractiveConeBeamReconstruction_GUI
pyuic5 -x $filename.ui -o $filename.py