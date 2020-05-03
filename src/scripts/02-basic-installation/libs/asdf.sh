#!/bin/bash

install_asdf() {
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

  # Install asdf-vm
  msg_step "Install asdf-vm"

  # clone from git
  msg_normal "clone from git"
  mute git clone https://github.com/asdf-vm/asdf.git ~/.asdf

  # checkout to latest version
  msg_normal "checkout to latest version"
  mute git -C ~/.asdf checkout "$(git -C ~/.asdf describe --abbrev=0 --tags)"
}
