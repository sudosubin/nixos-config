#!/bin/bash

install_bat() {
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

  # Configure bat
  msg_step "Configure bat"

  # settings
  msg_normal "copy settings"
  mkdir -p ~/.config/bat
  cp "$script_dir/settings/bat.config" ~/.config/bat/config
}
