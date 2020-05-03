#!/bin/bash

install_hello() {
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

  # Build hello
  msg_step "Build hello"

  # clone from git
  msg_normal "clone from git"
  mute git clone https://github.com/n4n0GH/hello.git ./temp-git

  # checkout to order version
  msg_normal "checkout to older version (transparency shades fix)"
  mute git -C temp-git checkout 3a4d3e2530109280b4bc8bd472e6c2037176839b

  # build hello window-decoration (only stderr)
  msg_normal "build hello window-decoration"
  mkdir -p temp-git/window-decoration/build
  cd temp-git/window-decoration/build || exit
  {
    silent cmake -DCMAKE_INSTALL_PREFIX=/usr ..
    silent make
  } | output_box cat

  # install hello window-decoration
  msg_normal "install hello window-decoration"
  silent sudo make install
  cd ../../..

  # build hello kwin-effects (only stderr)
  msg_normal "build hello kwin-effects"
  mkdir -p temp-git/kwin-effects/qt5build
  cd temp-git/kwin-effects/qt5build || exit
  {
    silent cmake -DCMAKE_INSTALL_PREFIX=/usr -DQT5BUILD=ON ..
    silent make
  } | output_box cat

  # install hello kwin-effects
  msg_normal "install hello kwin-effects"
  silent sudo make install
  cd ../../..

  # clean up
  msg_normal "clean up"
  rm -rf temp-git
}
