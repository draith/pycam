#!/bin/sh
echo "Stream available via vlc tcp/h264://192.168.0.60:3333"
raspivid -t 0 -l -o tcp://0.0.0:3333
