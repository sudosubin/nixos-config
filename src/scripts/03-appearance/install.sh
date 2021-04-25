#!/bin/bash

scripts_03() {
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

  # 03. Appearance
  msg_title "03. Appearance"

  # Global theme
  msg_heading "Global theme"
  set_global_theme

  # Fonts
  msg_heading "Fonts"
  set_fonts

  # Icons
  msg_heading "Icons"
  set_icons

  # Cursors
  msg_heading "Cursors"
  set_cursors
}
