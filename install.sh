#!/bin/bash

# Project Root Directory
APP_DIR="$(dirname "$(realpath "$0")")"

# 01. Software
# shellcheck source=src/scripts/01-software/install.sh
source "$APP_DIR/src/scripts/01-software/install.sh"
