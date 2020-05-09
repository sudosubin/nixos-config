#!/bin/bash

set_workspace_behaviors() {
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

  # General behavior
  msg_step "General behavior"
  msg_normal "change scrollbar click not to navigate page"
  kwriteconfig5 --file kdeglobals --group KDE \
    --key ScrollbarLeftClickNavigatesByPage false
  local search_pattern="^Gtk\/PrimaryButtonWarpsSlider.*"
  local replace_pattern="Gtk/PrimaryButtonWarpsSlider 1"
  sed -i -E "s|$search_pattern|$replace_pattern|g" \
    ~/.config/xsettingsd/xsettingsd.conf
  
  # Desktop Effects
  msg_step "Desktop Effects"
  msg_normal "enable wobbly windows"
  kwriteconfig5 --file kwinrc --group Plugins --key wobblywindowsEnabled true
  msg_normal "enable din screen"
  kwriteconfig5 --file kwinrc --group Plugins --key kwin4_effect_dimscreenEnabled true
  msg_normal "enable glide"
  kwriteconfig5 --file kwinrc --group Plugins --key glideEnabled true
  msg_normal "disable fade effect"
  kwriteconfig5 --file kwinrc --group Plugins --key kwin4_effect_fadeEnabled false

  # Screen edges
  msg_step "Screen edges"
  msg_normal "disable all screen edges"
  kwriteconfig5 --file kwinrc --group ElectricBorders --key TopLeft None
  kwriteconfig5 --file kwinrc --group Effect-PresentWindows --key BorderActivateAll 9

  # Screen locking
  msg_step "Screen locking"
  msg_normal "change timeout to 60m, 60s"
  kwriteconfig5 --file kscreenlockerrc --group Daemon --key LockGrace 60
  kwriteconfig5 --file kscreenlockerrc --group Daemon --key Timeout 60

  # Virtual desktops
  msg_step "Virtual desktops"
  msg_normal "enable switching osd"
  kwriteconfig5 --file kwinrc --group Plugins \
    --key desktopchangeosdEnabled true
  kwriteconfig5 --file kwinrc --group Script-desktopchangeosd \
    --key TextOnly true
  kwriteconfig5 --file kwinrc --group Script-desktopchangeosd \
    --key PopupHideDelay 500
  # kwriteconfig5 --file kwinrc --group Effect-Slide --key SlideDocks true
}
