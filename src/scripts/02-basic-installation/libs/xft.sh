#!/bin/bash

install_xft() {
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

  # Configure xft (emoji support)
  msg_step "Configure xft"

  msg_normal "clone from git"
  mute git clone https://gitlab.freedesktop.org/xorg/lib/libxft.git ./temp-git

  msg_normal "install xft"
  cd temp-git || exit
  wget -qO- \
    'https://gitlab.freedesktop.org/xorg/lib/libxft/merge_requests/1.patch' \
    | patch -p1
  {
    silent autoreconf --force --install
    silent ./configure
    silent make
    silent sudo make install
  } | output_box cat

  msg_normal "linking symlink"
  sudo ln -sfn /usr/local/lib/libXft.so.2.3.3 \
    /usr/lib/x86_64-linux-gnu/libXft.so.2.3.3

  msg_normal "clean up"
  sudo ldconfig
  cd ..
  rm -rf temp-git
}
