#!/bin/bash

# Directory
CURRENT_DIR="$(dirname "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$CURRENT_DIR")"
APP_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"

# Function
# shellcheck source=../../../../src/utils/msg.sh
source "$APP_DIR/src/utils/msg.sh" ":"
# shellcheck source=../../../../src/utils/stdout.sh
source "$APP_DIR/src/utils/stdout.sh" ":"

# Add ppa: add apt repository
msg_line "add apt repository"
vscodium_repo="https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo"
add_ppa vscodium \
  "$vscodium_repo/raw/master/pub.gpg" \
  "deb $vscodium_repo/raw/repos/debs/ vscodium main"

# Add ppa: add apt hooks
msg_line "add apt hooks (proposed api)"
sudo cp "$SCRIPT_DIR/hooks/vscodium-upgrade-helper" \
  /usr/local/bin/vscodium-upgrade-helper
sudo chmod 777 /usr/local/bin/vscodium-upgrade-helper
echo 'DPkg::Post-Invoke {"/usr/local/bin/vscodium-upgrade-helper";};' \
  | silent sudo tee -a /etc/apt/apt.conf.d/80upgradehook
