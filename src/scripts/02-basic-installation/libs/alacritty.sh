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

  # Configure alacritty
  msg_step "Configure alacritty"

  msg_normal "copy settings to local"
  mkdir -p ~/.config/alacritty
  cp "$script_dir/settings/alacritty.yml" ~/.config/alacritty/alacritty.yml

  msg_normal "make alacritty as a default shell"
  kwriteconfig5 --file kdeglobals --group General \
    --key TerminalApplication "alac"

  msg_normal "change global shortcuts"
  sed -i -e "s|Ctrl+Alt+T||g" ~/.config/kglobalshortcutsrc
  kwriteconfig5 --file khotkeysrc --group Data_1_2 --key Enabled false

  kwriteconfig5 --file kglobalshortcutsrc \
    --group com.alacritty.Alacritty.desktop \
    --key New "none,none,New Terminal"
  kwriteconfig5 --file kglobalshortcutsrc \
    --group com.alacritty.Alacritty.desktop \
    --key _k_friendly_name "Launch Alacritty"
  kwriteconfig5 --file kglobalshortcutsrc \
    --group com.alacritty.Alacritty.desktop \
    --key _launch "Ctrl+Alt+T,none,Launch Alacritty"
}
