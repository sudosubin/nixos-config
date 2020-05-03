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
sudo add-apt-repository -ny ppa:saiarcot895/chromium-dev

# Add ppa: add Google api key
msg_line "add google api key"
cp "$SCRIPT_DIR/keys/google-api-key" ~/.zprofile

# Add ppa: add apt hooks
msg_line "add apt hooks (dark mode)"
sudo cp "$SCRIPT_DIR/hooks/chromium-upgrade-helper" \
  /usr/local/bin/chromium-upgrade-helper
sudo chmod 777 /usr/local/bin/chromium-upgrade-helper
echo 'DPkg::Post-Invoke {"/usr/local/bin/chromium-upgrade-helper";};' \
  | silent sudo tee -a /etc/apt/apt.conf.d/80upgradehook
