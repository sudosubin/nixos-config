#!/bin/bash

install_plank() {
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

  # Configure plank
  msg_step "Configure plank"

  msg_normal "restore configurations"
  mkdir -p "$HOME/.config/autostart"
  dconf load /net/launchpad/plank/docks/ < \
    "$script_dir/settings/plank/settings.ini"
  cp "$script_dir/settings/plank/autostart.desktop" \
    "$HOME/.config/autostart/plank.desktop"

  msg_normal "copy pinned items"
  mkdir -p ~/.config/plank/dock1/launchers
  cp "$script_dir/settings/plank/chromium.dockitem" \
    ~/.config/plank/dock1/launchers/chromium.dockitem
  cp "$script_dir/settings/plank/st.dockitem" \
    ~/.config/plank/dock1/launchers/st.dockitem
  cp "$script_dir/settings/plank/org.kde.dolphin.dockitem" \
    ~/.config/plank/dock1/launchers/org.kde.dolphin.dockitem

  msg_normal "copy theme"
  mkdir -p ~/.local/share/plank/themes/OneWhite
  cp "$script_dir/settings/plank/dock.theme" \
    ~/.local/share/plank/themes/OneWhite/dock.theme
}
