#!/bin/bash

cd /home/pi/
export DISPLAY=:0
x='X -nocursor :0'
$x &
/usr/bin/xset dpms force on
$( which python ) server.py &
$( which python ) frame.py
$( which pkill ) X
$( which pkill ) python
