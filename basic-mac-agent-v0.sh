#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Basic Mac Agent V0
# @raycast.mode silent

pkill -f basic-mac-agent-v0.py
sleep 0.5
python3.14 ~/basic-mac-agent-v0/basic-mac-agent-v0.py
