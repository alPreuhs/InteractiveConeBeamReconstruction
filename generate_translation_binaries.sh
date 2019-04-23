#!/bin/bash -x
bindir=/home/cip/medtech2011/qi55wyqu/ciptmp/FPCTR/InteractiveReconstruction/venv/bin
langdir=languages
if type -P "lrelease" &>/dev/null; then
    exe=lrelease
else
    exe=$bindir/lrelease
fi
$exe $langdir/en_GB.ts
$exe $langdir/de_DE.ts