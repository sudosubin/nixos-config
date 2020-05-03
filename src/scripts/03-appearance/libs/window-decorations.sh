#!/bin/bash

set_window_decorations() {
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

  # Set window decorations: Breeze Dark
  msg_step "Set window decorations: hello"

  # window button layout (gsettings)
  gsettings set org.gnome.desktop.wm.preferences \
    button-layout "close,minimize,maximize:"

  # window button layout (plasma)
  kwriteconfig5 --file kwinrc --group org.kde.kdecoration2 \
    --key ButtonsOnLeft "XIA"
  kwriteconfig5 --file kwinrc --group org.kde.kdecoration2 \
    --key ButtonsOnRight ''

  # window decoration setting
  kwriteconfig5 --file kwinrc --group org.kde.kdecoration2 \
    --key library "org.kde.hello"
  kwriteconfig5 --file kwinrc --group org.kde.kdecoration2 \
    --key theme "hello"

  # miscellaneous
  kwriteconfig5 --file kwinrc --group Windows \
    --key BorderlessMaximizedWindows true
  kwriteconfig5 --file hellorc --group Windeco \
    --key TitleBarHeightSpin 2
}
