#!/bin/bash

install_asdf() {
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
  # shellcheck disable=SC1090
  source "$HOME/.asdf/asdf.sh"

  # Install asdf-python
  msg_step "Install asdf-python"

  msg_normal "add plugin"
  output_box asdf plugin-add python

  # Install asdf-nodejs
  msg_step "Install asdf-nodejs"

  msg_normal "add plugin"
  output_box asdf plugin-add nodejs

  msg_normal "import gpg keys"
  output_box bash ~/.asdf/plugins/nodejs/bin/import-release-team-keyring
}
