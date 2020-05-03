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

  # Install via apt-get
  # - git curl: Basic for script installation
  # - nimf nimf-libhangul: Basic for Korean input
  # - latte-dock applet-window-buttons: For better appearance
  # - chromium-browser codium net-tools fzf yarn zsh: My personal preference
  # - cmake g++ extra-cmake-modules libkdecorations2-dev
  #   libkf5guiaddons-dev libkf5configwidgets-dev
  #   libkf5windowsystem-dev libkf5package-dev libqt5x11extras5-dev
  #   gettext pkg-config: Build-deps for kde-hello window decoration
  # - qttools5-dev libkf5crash-dev libkf5globalaccel-dev
  #   libkf5kio-dev libkf5notifications-dev
  #   kinit-dev kwin-dev: Build-deps for kde-hello kwin effects
  # - inkscape x11-apps: Build-deps for capitaine-cursors
  msg_step "Install packages via apt-get"
  output_box sudo apt-get -y --no-install-recommends install \
    git curl \
    nimf nimf-libhangul \
    latte-dock applet-window-buttons \
    chromium-browser codium net-tools fzf yarn zsh \
    cmake g++ extra-cmake-modules libkdecorations2-dev \
    libkf5guiaddons-dev libkf5configwidgets-dev \
    libkf5windowsystem-dev libkf5package-dev libqt5x11extras5-dev \
    gettext pkg-config \
    qttools5-dev libkf5crash-dev libkf5globalaccel-dev \
    libkf5kio-dev libkf5notifications-dev \
    kinit-dev kwin-dev \
    inkscape x11-apps
}