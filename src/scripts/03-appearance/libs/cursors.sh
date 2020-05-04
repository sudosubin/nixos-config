#!/bin/bash

set_cursors() {
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

  # Set cursors: capitaine-cursors
  msg_step "Set cursors: capitaine-cursors"

  # set cursors (gsettings)
  gsettings set org.gnome.desktop.interface cursor-theme "capitaine-cursors"

  # set cursors (plasma)
  kwriteconfig5 --file kcminputrc --group Mouse \
    --key cursorTheme "capitaine-cursors"

  # set cursors (etc)
  kwriteconfig5 --file ~/.config/gtk-3.0/settings.ini --group Settings \
    --key gtk-cursor-theme-name "capitaine-cursors"

  local search_pattern="^Gtk\/CursorThemeName.*"
  local replace_pattern="Gtk/CursorThemeName \"capitaine-cursors\""

  sed -i -E "s|$search_pattern|$replace_pattern|g" \
    ~/.config/xsettingsd/xsettingsd.conf

  local search_pattern="^gtk-cursor-theme-name.*"
  local replace_pattern="gtk-cursor-theme-name=\"capitaine-cursors\""

  sed -i -E "s|$search_pattern|$replace_pattern|g" ~/.gtkrc-2.0
}
