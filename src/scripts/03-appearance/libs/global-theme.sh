#!/bin/bash

set_global_theme() {
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

  # Install theme
  msg_step "Install theme"
  msg_normal "download theme from git"
  mute git clone https://github.com/vinceliuice/Qogir-kde.git ./temp-git

  msg_normal "install"
  cd temp-git || exit
  output_box ./install.sh
  cd ..

  msg_normal "clean up"
  rm -rf temp-git

  # Set global theme: Qogir Dark
  msg_step "Set global theme: Qogir Dark"
  lookandfeeltool -a com.github.vinceliuice.Qogir-dark
}
