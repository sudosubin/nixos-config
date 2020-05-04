#!/bin/bash

install_awscli() {
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

  # Download AWS CLI
  msg_step "Downlaod AWS CLI"

  msg_normal "download files from online"
  curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" \
    -o "awscliv2.zip"
  
  msg_normal "unzip fiels"
  silent unzip awscliv2.zip

  msg_normal "install"
  sudo ./aws/install
  rm -rf aws
}
