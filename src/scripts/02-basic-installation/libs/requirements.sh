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
  # - git curl wget: Basic for script installation
  # - nimf nimf-libhangul: Basic for Korean input
  # - pass pass-extension-otp oathtool xclip: My password manage
  # - latte-dock plank: For better appearance
  # - chromium-browser codium net-tools fzf ulauncher
  #   openvpn network-manager-openvpn
  #   slack-desktop spotify-client yarn alacritty tmux bat zsh: My personal preference
  # - cmake make g++ extra-cmake-modules libkdecorations2-dev
  #   libkf5guiaddons-dev libkf5configwidgets-dev
  #   libkf5windowsystem-dev libkf5package-dev libqt5x11extras5-dev
  #   gettext pkg-config: Build-deps for kde-hello window decoration
  # - qttools5-dev libkf5crash-dev libkf5globalaccel-dev
  #   libkf5kio-dev libkf5notifications-dev libqt5opengl5-dev
  #   kinit-dev kwin-dev: Build-deps for kde-hello kwin effects
  # - qtdeclarative5-dev libkf5plasma-dev libsm-dev plasma-workspace-dev
  #   libxcb-randr0-dev libkf5wayland-dev: Build-deps for applet-window-appmenu
  # - qtbase5-dev libkf5declarative-dev: Build-deps for applet-window-buttons
  # - resolvconf: network settings
  # - libharfbuzz-dev libxft-dev: Build-deps for st term
  # - xutils-dev: Build-deps for xft
  msg_step "Install packages via apt-get"
  output_box sudo apt-get -y --no-install-recommends install \
    git curl wget \
    nimf nimf-libhangul \
    pass pass-extension-otp oathtool xclip \
    latte-dock plank fonts-symbola \
    chromium-browser codium net-tools fzf ulauncher \
    openvpn network-manager-openvpn \
    slack-desktop spotify-client yarn alacritty tmux bat zsh \
    cmake make g++ extra-cmake-modules libkdecorations2-dev \
    libkf5guiaddons-dev libkf5configwidgets-dev libtool \
    libkf5windowsystem-dev libkf5package-dev libqt5x11extras5-dev \
    gettext pkg-config \
    qttools5-dev libkf5crash-dev libkf5globalaccel-dev \
    libkf5kio-dev libkf5notifications-dev libqt5opengl5-dev \
    kinit-dev kwin-dev \
    qtdeclarative5-dev libkf5plasma-dev libsm-dev plasma-workspace-dev \
    libxcb-randr0-dev libkf5wayland-dev \
    qtbase5-dev libkf5declarative-dev \
    inkscape x11-apps \
    resolvconf \
    libharfbuzz-dev libxft-dev \
    xutils-dev
}
