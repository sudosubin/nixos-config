#!/bin/bash

install_tmux() {
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

  # Configure tmux
  msg_step "Configure tmux"

  msg_normal "install tpm"
  mute git clone https://github.com/tmux-plugins/tpm \
    ~/.tmux/plugins/tpm

  msg_normal "copy settings"
  cp "$script_dir/settings/.tmux.conf" "$HOME/.tmux.conf"
}
