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
  vscodium_io="https://paulcarroty.gitlab.io/vscodium-deb-rpm-repo"
  add_ppa vscodium \
    "$vscodium_repo/raw/master/pub.gpg" \
    "deb $vscodium_io/debs/ vscodium main"
}
