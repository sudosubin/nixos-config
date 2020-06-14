#!/bin/bash

install_delta() {
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

  # Install delta
  msg_step "Install delta"

  # settings
  msg_normal "download deb"
  local download="https://github.com/barnumbirr/delta-debian/releases/download"
  local version="0.1.1-2"
  curl -sL "$download/v$version/delta-diff_${version}_amd64_debian_buster.deb" \
    -o "delta.deb"

  msg_normal "install deb"
  output_box sudo dpkg -i delta.deb
  rm -r delta.deb
}