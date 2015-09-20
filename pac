#!/bin/sh

python pypac $1 > /tmp/pa_tmp.cpp
g++ -std=c++11 /tmp/pa_tmp.cpp -Iinclude -o ${2:-a.out}
rm /tmp/pa_tmp.cpp
