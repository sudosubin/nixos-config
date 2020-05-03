#!/bin/bash


# Directory
CURRENT_DIR="$(dirname "${BASH_SOURCE[0]}")"
APP_DIR="$(dirname "$(dirname "$(dirname "$CURRENT_DIR")")")"


# Function
# shellcheck source=../../../src/utils/msg.sh
source "$APP_DIR/src/utils/msg.sh" ":"
# shellcheck source=../../../src/utils/stdout.sh
source "$APP_DIR/src/utils/stdout.sh" ":"

# Function: easy add ppa
add_ppa() {
  wget -qO - "$2" | mute sudo apt-key add -
  echo "$3" | silent sudo tee "/etc/apt/sources.list.d/$1.list"
}


# Title
msg_title "01. Software"


# Change software sources mirror
msg_subtitle "Change software sources mirror"
msg_step "Change from ubuntu to kakao"
sudo sed -i -Ee "s|[a-z]{2}.archive.ubuntu.com|archive.ubuntu.com|g" \
  -e "/^#/!s/archive.ubuntu.com/mirror.kakao.com/" /etc/apt/sources.list


# Add ppa (launchpad ppa)
msg_subtitle "Add launchpad ppa"

## Add ppa: chromium-dev (non-snap)
msg_step "Add ppa: saiarcot895/chromium-dev"

### Add ppa: chromium-dev add apt repository
msg_line "add apt repository"
sudo add-apt-repository -ny ppa:saiarcot895/chromium-dev

### Add ppa: chromium-dev add Google api key
msg_line "add Google api key"
cat "$CURRENT_DIR/keys/google-api-key" > ~/.zprofile

### Add ppa: chromium-dev add apt hooks
msg_line "add apt hooks (dark mode)"
sudo cp "$CURRENT_DIR/hooks/chromium-upgrade-helper" \
  /usr/local/bin/chromium-upgrade-helper
sudo chmod 777 /usr/local/bin/chromium-upgrade-helper
echo 'DPkg::Post-Invoke {"/usr/local/bin/chromium-upgrade-helper";};' \
  | silent sudo tee -a /etc/apt/apt.conf.d/80upgradehook

## Add ppa: nimf (compatible 20.04)
msg_step "Add ppa: nemonein/nimf"
sudo add-apt-repository -ny ppa:nemonein/nimf

## Add ppa: kde-window-buttons
msg_step "Add ppa: krisives/applet-window-buttons"
sudo add-apt-repository -ny ppa:krisives/applet-window-buttons


# Add ppa (non-launchpad ppa)
msg_subtitle "Add non-launchpad ppa"

## Add ppa: vscodium
msg_step "Add ppa: paulcarroty/vscodium"

### Add ppa: vscodium add apt repository
msg_line "add apt repository"
vscodium_repo="https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo"
add_ppa vscodium \
  "$vscodium_repo/raw/master/pub.gpg" \
  "deb $vscodium_repo/raw/repos/debs/ vscodium main"

### Add ppa: vscodium add apt hooks
msg_line "add apt hooks (proposed api)"
sudo cp "$CURRENT_DIR/hooks/vscodium-upgrade-helper" \
  /usr/local/bin/vscodium-upgrade-helper
sudo chmod 777 /usr/local/bin/vscodium-upgrade-helper
echo 'DPkg::Post-Invoke {"/usr/local/bin/vscodium-upgrade-helper";};' \
  | silent sudo tee -a /etc/apt/apt.conf.d/80upgradehook

## Add ppa: yarn
msg_step "Add ppa: yarn"
yarn_repo="https://dl.yarnpkg.com"
add_ppa yarn \
  "$yarn_repo/debian/pubkey.gpg" \
  "deb $yarn_repo/debian/ stable main"


# Remove package
msg_subtitle "Remove package"

## Remove package: firefox
msg_step "Remove package: firefox"
silent sudo apt-get -y remove --purge firefox

## Remove package: finish
msg_step "Remove package: clean up packages"
silent sudo apt-get -y --purge autoremove
silent sudo apt-get -y clean


# Update & Upgrade (no silent mode)
msg_subtitle "Update & upgrade packages"

## Update & Upgrade: Update packages
msg_step "Update packages"
hr
sudo apt-get update
hr
new_line

## Update & Upgrade: Upgrade packages
msg_step "Upgrade packages"
hr
sudo apt-get -y upgrade
hr
