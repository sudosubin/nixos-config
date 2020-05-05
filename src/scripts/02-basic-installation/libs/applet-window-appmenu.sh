#!/bin/bash

install_applet_window_appmenu() {
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

  # Build applet-window-appmenu
  msg_step "Build psifidotos/applet-window-appmenu"

  msg_normal "download from git"
  mute git clone https://github.com/psifidotos/applet-window-appmenu.git \
    ./temp-git

  msg_normal "build and install"
  cd temp-git || exit
  output_box silent sh install.sh
  cd ..

  msg_normal "clean up"
  rm -rf temp-git
}
