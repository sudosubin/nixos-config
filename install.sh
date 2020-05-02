#!/bin/bash

# Project Root Directory
APP_DIR="$(dirname "$(readlink -fm "$0")")"

# Install step by step
## 01. Software
bash "$APP_DIR/src/scripts/01-software/install.sh"
bash "$APP_DIR/src/"
