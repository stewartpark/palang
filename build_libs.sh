#!/bin/sh

echo PAC tcp.cc
python pypac libs/tcp.cc -l -o libs/tcp.so
echo PAC file.cc
python pypac libs/file.cc -l -o libs/file.so
echo PAC string.pa
python pypac libs/string.pa -l -o libs/string.so
