#!/bin/bash

install_spotify() {
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

  # Configure spotify
  msg_step "Configure spotify"

  msg_normal "install spicetify-cli"
  {
    curl -fsSL https://raw.githubusercontent.com/khanhas/spicetify-cli/master/install.sh | sh
    ~/spicetify-cli/spicetify
  } | output_box cat

  msg_normal "install spicetify-themes"
  mute git clone https://github.com/morpheusthewhite/spicetify-themes.git \
    ~/.config/spicetify/Themes

  msg_normal "applying flatten theme"
  {
    sudo chmod a+wr /usr/share/spotify
    sudo chmod a+wr /usr/share/spotify/Apps -R
    ~/spicetify-cli/spicetify config current_theme "Flatten"
    ~/spicetify-cli/spicetify apply
  } | output_box cat
}
