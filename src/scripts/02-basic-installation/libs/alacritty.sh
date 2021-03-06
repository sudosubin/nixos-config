#!/bin/bash

install_alacritty() {
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

  # Configure st
  msg_step "Configure alacritty"

  msg_normal "make alacritty as a default shell"

  kwriteconfig5 --file kdeglobals --group General \
    --key TerminalApplication "alac"

  msg_normal "change global shortcuts"

  sudo ln -s /usr/share/applications/com.alacritty.Alacritty.desktop \
    /usr/share/kglobalaccel/com.alacritty.Alacritty.desktop

  kwriteconfig5 --file kglobalshortcutsrc \
    --group com.alacritty.Alacritty.desktop \
    --key New "none,none,New Terminal"
  kwriteconfig5 --file kglobalshortcutsrc \
    --group com.alacritty.Alacritty.desktop \
    --key _k_friendly_name "Launch Terminal"
  kwriteconfig5 --file kglobalshortcutsrc \
    --group com.alacritty.Alacritty.desktop \
    --key _launch "Ctrl+Alt+T,none,Launch Terminal"
}
