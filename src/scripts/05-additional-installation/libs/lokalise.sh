#!/bin/bash

install_lokalise() {
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

  # Default git hooks
  msg_step "Install lokalise cli v2"

  msg_normal "install lokalise cli v2"
  output_box curl -sfL https://raw.githubusercontent.com/lokalise/lokalise-cli-2-go/master/install.sh | sh
  sudo mv "./bin/lokalise2" "/usr/local/bin/lokalise2"
}
