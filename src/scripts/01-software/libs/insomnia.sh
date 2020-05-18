#!/bin/bash

add_ppa_insomnia() {
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

  # Add ppa: insomnia
  msg_step "Add ppa: insomnia"

  # add apt repository
  msg_normal "add apt repository"
  add_ppa insomnia \
    "https://insomnia.rest/keys/debian-public.key.asc" \
    "deb https://dl.bintray.com/getinsomnia/Insomnia /"
}
