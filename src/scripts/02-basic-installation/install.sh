#!/bin/bash

scripts_02() {
  # Directory
  local current_dir
  local app_dir

  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  app_dir="$(dirname "$(dirname "$(dirname "$current_dir")")")"

  # Function
  # shellcheck source=../../../src/utils/msg.sh
  source "$app_dir/src/utils/msg.sh"
  # shellcheck source=../../../src/utils/stdout.sh
  source "$app_dir/src/utils/stdout.sh"
  # shellcheck source=libs/index.sh
  source "$current_dir/libs/index.sh"

  # 02. Basic Installation
  msg_title "02. Basic Installation"

  # Install softwares
  msg_heading "Install softwares"
  install_requirements
  install_asdf
  install_latte
  install_zsh

  # Configure softwares
  msg_heading "Configure softwares"
  install_alacritty
  install_nimf
  install_plank
  install_rclone
  install_ulauncher
  install_vscodium

  # Build softwares
  msg_heading "Build softwares"
  install_applet_window_appmenu
  install_capitaine_cursors
  install_la_capitaine_icon_theme
  install_hello
}
