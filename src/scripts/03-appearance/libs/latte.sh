#!/bin/bash

set_latte() {
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

  # Configure latte window colors script
  msg_step "Configure latte window colors script"
  kwriteconfig5 --file kwinrc --group Plugins \
    --key lattewindowcolorsEnabled true

  # Remove default panel
  msg_stpe "Remove default panels"
  sed -i \
    -e '/./{H;$!d;}' -e 'x;/ActionPlugins/b' \
    -e '/[9]/b' -e '/ScreenMapping/b' -e d ~/.config/plasma-org.kde.plasma.desktop-appletsrc

  # Configure latte layout
  msg_step "Configure latte layout"
  mkdir -p ~/.config/latte
  # TODO (sudosubin): rewrite and optimize layout.latte file
  cp "$script_dir/assets/Panel.layout.latte" ~/.config/latte/Panel.layout.latte
  kwriteconfig5 --file lattedockrc --group UniversalSettings \
    --key currentLayout "Panel"
  kwriteconfig5 --file lattedockrc --group UniversalSettings \
    --key lastNonAssignedLayout "Panel"
}
