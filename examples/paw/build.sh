#!/usr/bin/env bash

if [ -z $PA_HOME ]; then
    echo PA_HOME is not set.;
    exit 1
fi;

PAC="python $PA_HOME/pypac"

echo PAC libs/paw.pa
$PAC libs/paw.pa -l -o libs/paw.so $@
echo PAC app.pa
$PAC app.pa -o app $@
