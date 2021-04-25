#!/bin/bash

install_requirements() {
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

  # Update new ppa sources
  msg_step "Update new ppa sources"
  output_box sudo apt-get update

  # Install via apt-get
  # - sway rofi xwayland: Window compositor
  # - pass pass-extension-otp oathtool xclip gnome-keyring: Password
  # - resolvconf openvpn: Network
  # - policykit-1 policykit-1-gnome policykit-desktop-privileges: Permission
  # - arc-theme: Theme
  # - bat docker.io docker-compose fzf gpg jq shellcheck tmux watchman
  #     zsh: Development
  # - alacritty google-chrome-stable insomnia gh slack-desktop spotify-client
  #     codium yarn: Install from ppa
  msg_step "Install packages via apt-get"
  output_box sudo apt-get -y --no-install-recommends install \
    sway rofi xwayland \
    pass pass-extension-otp oathtool xclip \
    resolvconf openvpn \
    policykit-1 policykit-1-gnome policykit-desktop-privileges \
    arc-theme \
    bat docker.io docker-compose fzf gpg jq shellcheck tmux watchman \
      zsh \
    alacritty google-chrome-stable insomnia gh slack-desktop spotify-client \
      codium yarn
}
