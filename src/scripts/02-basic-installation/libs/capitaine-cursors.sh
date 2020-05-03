#!/bin/bash

install_capitaine_cursors() {
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

  # Build capitaine-cursors
  msg_step "Build capitaine-cursors"

  # clone from git
  msg_normal "clone from git"
  mute git clone https://github.com/keeferrourke/capitaine-cursors.git \
    ./temp-git

  # build capitaine-cursors
  msg_normal "build capitaine-cursors (takes long time)"
  cd temp-git || exit
  mute ./build.sh -t dark
  cd ..

  # copy to cursors directory
  msg_normal "copy to cursors directory"
  cp -r temp-git/dist/dark ~/.icons/capitaine-cursors

  # clean up
  msg_normal "clean up"
  rm -rf temp-git
}
