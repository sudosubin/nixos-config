#!/bin/bash

add_ppa_jetbrains() {
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
  # shellcheck source=../../../../src/utils/ppa.sh
  source "$app_dir/src/utils/ppa.sh"

  # Add ppa: JonasGroeger/jetbrains
  msg_step "Add ppa: JonasGroeger/jetbrains"

  # add apt repository
  msg_normal "add apt repository"
  add_ppa jetbrains \
    "https://s3.eu-central-1.amazonaws.com/jetbrains-ppa/0xA6E8698A.pub.asc" \
    "deb http://jetbrains-ppa.s3-website.eu-central-1.amazonaws.com bionic main"
}
