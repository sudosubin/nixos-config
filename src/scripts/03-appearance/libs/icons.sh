#!/bin/bash

set_icons() {
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

  # Set icons: la-capitaine-icon-theme
  msg_step "Set icons: la-capitaine-icon-theme"

  # set icons (gsettings)
  gsettings set org.gnome.desktop.interface \
    icon-theme "la-capitaine-icon-theme"

  # set icons (plasma)
  kwriteconfig5 --file kdeglobals --group Icons \
    --key Theme "la-capitaine-icon-theme"

  # set icons (etc)
  kwriteconfig5 --file ~/.config/gtk-3.0/settings.ini --group Settings \
    --key gtk-icon-theme-name "la-capitaine-icon-theme"

  local search_pattern="^Net\/IconThemeName.*"
  local replace_pattern="Net/IconThemeName \"la-capitaine-icon-theme\""

  sed -i -E "s|$search_pattern|$replace_pattern|g" \
    ~/.config/xsettingsd/xsettingsd.conf

  local search_pattern="^gtk-icon-theme-name.*"
  local replace_pattern="gtk-icon-theme-name=\"la-capitaine-icon-theme\""

  sed -i -E "s|$search_pattern|$replace_pattern|g" ~/.gtkrc-2.0
}
