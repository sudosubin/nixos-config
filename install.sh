#!/bin/bash

# Project Root Directory
APP_DIR="$(dirname "$(realpath "$0")")"

# 00. Get permission
# shellcheck source=src/utils/sudo.sh
source "$APP_DIR/src/utils/sudo.sh"
get_sudo

# 01. Software
# shellcheck source=src/scripts/01-software/install.sh
source "$APP_DIR/src/scripts/01-software/install.sh"

# 02. Basic Installation
# shellcheck source=src/scripts/02-basic-installation/install.sh
source "$APP_DIR/src/scripts/02-basic-installation/install.sh"

# TODO: Additional Installation (for development)
