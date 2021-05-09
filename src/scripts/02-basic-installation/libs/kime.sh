#!/bin/bash

install_kime() {
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

  # Install kime
  msg_step "Install kime"

  # downlaod kime
  msg_normal "download kime from github release"
  curl -sL \
    https://github.com/Riey/kime/releases/download/v2.5.2/kime_ubuntu-20.04_v2.5.2_amd64.deb \
    -o kime.deb

  # install kime
  msg_normal "install kime"
  silent sudo dpkg -i kime.deb

  # clean up
  msg_normal "clean up"
  rm -rf kime.deb
}
