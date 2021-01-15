#!/bin/bash

add_ppa_groovy() {
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

  # Add ppagroovy
  msg_step "Add groovy release packages"

  # add apt repository
  msg_normal "copy configurations"
  sudo cp "$script_dir/settings/priority-ubuntu" \
    /etc/apt/preferences.d/priority-ubuntu
  sudo cp "$script_dir/settings/sources-groovy.list" \
    /etc/apt/sources.list.d/sources-groovy.list
}
