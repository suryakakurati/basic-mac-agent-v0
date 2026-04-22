#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Jarvis
# @raycast.mode silent

pkill -f jarvis.py
sleep 0.5
python3.14 ~/jarvis/jarvis.py
