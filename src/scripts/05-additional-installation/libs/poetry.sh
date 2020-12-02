#!/bin/bash

install_poetry() {
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

  msg_step "Install poetry"

  msg_normal "installaing"
  {
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py \
      | python3
  } | output_box cat
}
