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
  # - mako-notifier sway rofi waybar xwayland: Window compositor
  # - apparmor-utils: Fix mako
  # - grim slurp wl-clipboard: Screenshot
  # - nautilus: File Explorer
  # - pass pass-extension-otp oathtool xclip gnome-keyring: Password
  # - resolvconf openvpn: Network
  # - pulseaudio pavucontrol: Audio
  # - lxpolkit: Permission
  # - arc-theme: Theme
  # - bat docker.io docker-compose fzf gpg jq shellcheck tmux watchman
  #     zsh: Development
  # - make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev
  #     libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev
  #     libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev: Python Development
  # - unzip: Kotlin Development
  # - alacritty google-chrome-stable insomnia gh slack-desktop spotify-client
  #     codium yarn: Install from ppa
  msg_step "Install packages via apt-get"
  output_box sudo apt-get -y --no-install-recommends install \
    mako-notifier sway rofi waybar xwayland \
    grim slurp wl-clipboard \
    nautilus \
    pass pass-extension-otp oathtool xclip gnome-keyring \
    resolvconf openvpn \
    pulseaudio pavucontrol \
    lxpolkit \
    arc-theme \
    bat docker.io docker-compose fzf gpg jq shellcheck tmux watchman \
      zsh \
    make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
      libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev \
      libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
    unzip \
    alacritty google-chrome-stable gh slack-desktop spotify-client \
      codium yarn
}
