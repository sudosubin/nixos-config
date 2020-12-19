#!/bin/bash

install_zpl() {
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

  # Install zpl
  msg_step "Install zpl (zeplin uri handler)"

  # settings
  msg_normal "clone from git"
  mute git clone https://github.com/sudosubin/zeplin-uri-opener.git ./temp-git
  bash temp-git/install.sh

  msg_normal "clean up"
  rm -rf temp-git
}
