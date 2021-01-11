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

  # Download cursor theme
  msg_step "Download from github release"
  curl -sL \
    https://github.com/ful1e5/apple_cursor/releases/latest/download/macOSBigSur.tar.gz \
    -o "apple-cursor.tar.gz"

  mkdir -p ~/.icons/apple-cursor
  tar -xf apple-cursor.tar.gz -C ~/.icons/apple-cursor --strip-components=1
  rm -rf apple-cursor.tar.gz

  # Set cursors: apple-cursor
  msg_step "Set cursors: apple-cursor"

  # set cursors (gsettings)
  gsettings set org.gnome.desktop.interface cursor-theme "apple-cursor"
  gsettings set org.gnome.desktop.interface cursor-size 22

  # set cursors (plasma)
  kwriteconfig5 --file kcminputrc --group Mouse --key cursorTheme "apple-cursor"
  kwriteconfig5 --file kcminputrc --group Mouse --key cursorSize 22

  # set cursors (etc)
  kwriteconfig5 --file ~/.config/gtk-3.0/settings.ini --group Settings \
    --key gtk-cursor-theme-name "apple-cursor"

  local search_pattern="^Gtk\/CursorThemeName.*"
  local replace_pattern="Gtk/CursorThemeName \"apple-cursor\""

  sed -i -E "s|$search_pattern|$replace_pattern|g" \
    ~/.config/xsettingsd/xsettingsd.conf

  local search_pattern="^gtk-cursor-theme-name.*"
  local replace_pattern="gtk-cursor-theme-name=\"apple-cursor\""

  sed -i -E "s|$search_pattern|$replace_pattern|g" ~/.gtkrc-2.0
}
