#!/bin/bash

install_latte() {
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

  # Download latte applets
  msg_step "Download latte applets"

  # psifidotos/applet-latte-spacer
  msg_normal "download psifidotos/applet-latte-spacer"
  mute git clone https://github.com/psifidotos/applet-latte-spacer.git \
    ./temp-git
  mute plasmapkg2 -i temp-git
  rm -rf temp-git

  # psifidotos/applet-window-title
  msg_normal "download psifidotos/applet-window-title"
  mute git clone https://github.com/psifidotos/applet-window-title.git \
    ./temp-git
  mute plasmapkg2 -i temp-git
  rm -rf temp-git
  
  # varlesh/org.kde.plasma.digitalclock.wl
  msg_normal "download psifidotos/org.kde.plasma.digitalclock.wl"
  mute git clone https://github.com/varlesh/org.kde.plasma.digitalclock.wl.git \
    ./temp-git
  mute plasmapkg2 -i temp-git
  rm -rf temp-git

  # Install color script
  msg_step "Install kwin script"

  # psifidotos/kwinscript-window-colors
  msg_normal "download psifidotos/kwinscript-window-colors"
  mute git clone https://github.com/psifidotos/kwinscript-window-colors.git \
    ./temp-git
  mute plasmapkg2 -i temp-git
  rm -rf temp-git
}
