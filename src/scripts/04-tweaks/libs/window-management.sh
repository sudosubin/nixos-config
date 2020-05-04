#!/bin/bash

set_window_management() {
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

  # Window behavior
  msg_step "Window behavior"
  msg_normal "modify titlebar actions"
  kwriteconfig5 --file kwinrc --group Windows --key AutoRaiseInterval 750
  kwriteconfig5 --file kwinrc --group Windows --key DelayFocusInterval 300
  kwriteconfig5 --file kwinrc --group MouseBindings \
    --key CommandTitlebarWheel "Shade/Unshade"

  msg_normal "modify window actions"
  kwriteconfig5 --file kwinrc --group MouseBindings --key CommandAllKey "Meta"

  msg_normal "make default window position to center"
  kwriteconfig5 --file kwinrc --group Windows --key Placement "Centered"

  # Task switcher
  msg_step "Task switcher"
  msg_normal "change layout, delay time"
  kwriteconfig5 --file kwinrc --group TabBox --key LayoutName "thumbnail_grid"
  kwriteconfig5 --file kwinrc --group TabBox --key DelayTime 0
  kwriteconfig5 --file kwinrc --group TabBox --key HighlightWindows false
}
