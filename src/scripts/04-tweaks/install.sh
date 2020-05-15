#!/bin/bash

scripts_04() {
  # Directory
  local current_dir
  local app_dir

  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  app_dir="$(dirname "$(dirname "$(dirname "$current_dir")")")"

  # Function
  # shellcheck source=../../../src/utils/msg.sh
  source "$app_dir/src/utils/msg.sh"
  # shellcheck source=../../../src/utils/stdout.sh
  source "$app_dir/src/utils/stdout.sh"
  # shellcheck source=libs/index.sh
  source "$current_dir/libs/index.sh"

  # 04. Tweaks
  msg_title "04. Tweaks"

  # Workspace behavior
  msg_heading "Workspace behaviors"
  set_workspace_behaviors

  # Window management
  msg_heading "Window management"
  set_window_management

  # Keyboard & Mouse
  msg_heading "Keyboard & Mouse"
  set_keyboard_and_mouse

  # Plasma etc
  msg_heading "Plasma etc"
  set_plasma_etc

  # Network
  msg_heading "Network"
  set_network
}
