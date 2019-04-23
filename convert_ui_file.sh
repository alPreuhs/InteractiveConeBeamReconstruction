#!/bin/bash -x
bindir=/home/cip/medtech2011/qi55wyqu/ciptmp/FPCTR/InteractiveReconstruction/venv/bin
filename=InteractiveConeBeamReconstruction_GUI
if type -P "pyuic5" &>/dev/null; then
    exe=pyuic5
else
    exe=$bindir/pyuic5
fi
$exe -x $filename.ui -o $filename.py