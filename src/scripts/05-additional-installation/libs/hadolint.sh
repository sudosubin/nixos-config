#!/bin/bash

install_hadolint() {
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

  msg_step "Install hadolint"

  msg_normal "download from git"
  local download="https://github.com/hadolint/hadolint/releases/download"
  local version="v1.19.0"
  curl -sL "$download/$version/hadolint-Linux-x86_64" \
    -o "hadolint"

  msg_normal "installation"
  sudo mv ./hadolint /usr/local/bin/hadolint
  sudo chmod a+x /usr/local/bin/hadolint
}
