#!/bin/bash

add_ppa_vscode() {
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

  # Add ppa: vscode
  msg_step "Add ppa: vscode"

  # add apt repository
  msg_normal "add gpg"
  silent curl https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor > packages.microsoft.gpg
  mute sudo apt-key add packages.microsoft.gpg
  rm -r packages.microsoft.gpg

  msg_normal "add apt repository"
  echo \
    "deb [arch=amd64] https://packages.microsoft.com/repos/vscode stable main" \
    | silent sudo tee "/etc/apt/sources.list.d/vscode.list"
}
