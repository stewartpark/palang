#!/bin/sh

python pypac libs/tcp.cc -l -o libs/tcp.so
python pypac libs/file.cc -l -o libs/file.so
python pypac libs/string.pa -l -o libs/string.so
