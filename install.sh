#!/bin/bash

# Project Root Directory
APP_DIR="$(dirname "$(realpath "$0")")"

# Function
# shellcheck source=src/utils/sudo.sh
source "$APP_DIR/src/utils/sudo.sh"
# shellcheck source=src/scripts/index.sh
source "$APP_DIR/src/scripts/index.sh"

# 00. Get permission
get_sudo

# 01. Software
scripts_01

# 02. Basic Installation
scripts_02

# 03. Appearance
scripts_03

# TODO: Additional Installation (for development)
