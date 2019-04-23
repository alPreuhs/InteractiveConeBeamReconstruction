#!/bin/bash -x
bindir=/home/cip/medtech2011/qi55wyqu/ciptmp/FPCTR/InteractiveReconstruction/venv/bin
langdir=languages
filename=InteractiveConeBeamReconstruction_GUI
if type -P "pylupdate5" &>/dev/null; then
    exe=pylupdate5
else
    exe=$bindir/pylupdate5
fi
$exe $filename.py -ts $langdir/en_GB.ts
$exe $filename.py -ts $langdir/de_DE.ts