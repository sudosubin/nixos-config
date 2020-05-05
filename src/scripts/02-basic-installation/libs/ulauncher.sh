#!/bin/bash

install_ulauncher() {
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

  # Configure ulauncher
  msg_step "Configure ulauncher"

  msg_normal "download theme from git"
  mkdir -p ~/.config/ulauncher/user-themes

  mute git clone https://github.com/sudosubin/one-dark-ulauncher.git \
    ~/.config/ulauncher/user-themes/one-dark-ulauncher

  msg_normal "copy icons, configurations"
  cp "$script_dir/settings/ulauncher/google.png" \
    ~/.local/share/icons/ulauncher/google.png
  
  cp "$script_dir/settings/ulauncher/settings.json" \
    ~/.config/ulauncher/settings.json

  cp "$script_dir/settings/ulauncher/shortcuts.json" \
    ~/.config/ulauncher/shortcuts.json

  msg_normal "disable krunner"
  kwriteconfig5 --file kglobalshortcutsrc --group krunner.desktop \
    --key _launch ",Alt+Space\tAlt+F2\tSearch,KRunner"

  # replace \\t to \t
  sed -i 's|\\\\t|\\t|g' ~/.config/kglobalshortcutsrc
}
