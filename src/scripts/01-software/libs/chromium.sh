#!/bin/bash

add_ppa_chromium() {
  # Directory
  local current_dir
  local script_dir
  local app_dir

  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  script_dir="$(dirname "$current_dir")"
  app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

  # shellcheck source=../../../../src/utils/msg.sh
  source "$app_dir/src/utils/msg.sh"
  # shellcheck source=../../../../src/utils/stdout.sh
  source "$app_dir/src/utils/stdout.sh"

  # Add debian repository
  msg_step "Add debian repository"

  # add apt repository
  msg_normal "add apt repository"
  sudo cp "$script_dir/settings/debian.list" \
    "/etc/apt/sources.list.d/debian.list"
  silent sudo apt-key add /usr/share/keyrings/debian-archive-keyring.gpg

  # copy pref
  sudo cp "$script_dir/settings/chromium.pref" \
    "/etc/apt/preferences.d/chromium.pref"

  # add Google api key
  msg_normal "add Google api key"
  cp "$script_dir/keys/google-api-key" ~/.zprofile

  # add apt hooks
  msg_normal "add apt hooks (dark mode)"
  sudo cp "$script_dir/hooks/chromium-upgrade-helper" \
    /usr/local/bin/chromium-upgrade-helper
  sudo chmod 777 /usr/local/bin/chromium-upgrade-helper
  echo 'DPkg::Post-Invoke {"/usr/local/bin/chromium-upgrade-helper";};' \
    | silent sudo tee /etc/apt/apt.conf.d/80upgradehook
}
