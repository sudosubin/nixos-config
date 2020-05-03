#!/bin/bash


# Directory
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
APP_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"


# Function
# shellcheck source=../../../src/utils/msg.sh
source "$APP_DIR/src/utils/msg.sh" ":"
# shellcheck source=../../../src/utils/stdout.sh
source "$APP_DIR/src/utils/stdout.sh" ":"
# shellcheck source=../../../src/utils/ppa.sh
source "$APP_DIR/src/utils/ppa.sh" ":"


# Title
msg_title "01. Software"


# Change software sources mirror
msg_subtitle "Change software sources mirror"
msg_step "Change from ubuntu to kakao"
sudo sed -i -Ee "s|[a-z]{2}.archive.ubuntu.com|archive.ubuntu.com|g" \
  -e "/^#/!s/archive.ubuntu.com/mirror.kakao.com/" /etc/apt/sources.list


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
new_line


# Add ppa (launchpad ppa)
msg_subtitle "Add ubuntu ppa"

## Add ppa: chromium-dev
msg_step "Add ppa: saiarcot895/chromium-dev"
# shellcheck source=libs/chromium.sh
source "$SCRIPT_DIR/libs/chromium.sh"

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
# shellcheck source=libs/vscodium.sh
source "$SCRIPT_DIR/libs/vscodium.sh"

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
