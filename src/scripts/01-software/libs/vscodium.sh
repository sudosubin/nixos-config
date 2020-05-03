#!/bin/bash

add_ppa_vscodium() {
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
  # shellcheck source=../../../../src/utils/ppa.sh
  source "$app_dir/src/utils/ppa.sh"

  # Add ppa: paulcarroty/vscodium
  msg_step "Add ppa: paulcarroty/vscodium"

  # add apt repository
  msg_normal "add apt repository"
  vscodium_repo="https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo"
  add_ppa vscodium \
    "$vscodium_repo/raw/master/pub.gpg" \
    "deb $vscodium_repo/raw/repos/debs/ vscodium main"

  # add apt hooks
  msg_normal "add apt hooks (proposed api)"
  sudo cp "$script_dir/hooks/vscodium-upgrade-helper" \
    /usr/local/bin/vscodium-upgrade-helper
  sudo chmod 777 /usr/local/bin/vscodium-upgrade-helper
  echo 'DPkg::Post-Invoke {"/usr/local/bin/vscodium-upgrade-helper";};' \
    | silent sudo tee -a /etc/apt/apt.conf.d/80upgradehook
}
