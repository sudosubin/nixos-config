#!/bin/bash

set_network() {
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

  # DNS
  msg_step "DNS"
  msg_normal "change dns nameserver"
  echo "nameserver 1.1.1.1" \
    | silent sudo tee -a /etc/resolvconf/resolv.conf.d/tail
  echo "nameserver 1.0.0.1" \
    | silent sudo tee -a /etc/resolvconf/resolv.conf.d/tail
  sudo resolvconf -u
  sudo service resolvconf restart
}
