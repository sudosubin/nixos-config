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
# shellcheck source=src/scripts/02-basic-installation/install.sh
source "$APP_DIR/src/scripts/02-basic-installation/install.sh"

# TODO: Additional Installation (for development)
