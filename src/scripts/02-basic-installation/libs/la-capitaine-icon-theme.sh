#!/bin/bash

install_la_capitaine_icon_theme() {
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

  # Build la-capitaine-icon-theme
  msg_step "Build la-capitaine-icon-theme"

  # clone from git
  msg_normal "clone from git"
  mute git clone https://github.com/keeferrourke/la-capitaine-icon-theme.git \
    ./temp-git

  # build la-capitaine-icon-theme
  msg_normal "build la-capitaine-icon-theme"
  cd temp-git || exit
  echo y | mute ./configure
  cd ..

  # copy to icon directory
  msg_normal "copy to icon directory"
  mkdir -p ~/.local/share/icons
  cp -r temp-git ~/.local/share/icons/la-capitaine-icon-theme

  # clean up
  msg_normal "clean up"
  rm -rf temp-git
}
