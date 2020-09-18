#!/bin/bash

set_plasma_etc() {
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

  # Configure locale
  msg_step "Configure locale"
  msg_normal "change locale to en_US.UTF-8"
  kwriteconfig5 --file plasma-localerc --group Formats --key useDetailed true
  kwriteconfig5 --file plasma-localerc --group Formats \
    --key LC_TIME "en_US.UTF-8"

  # Configure konsole
  # mkdir -p ~/.local/share/konsole
  # curl -sL https://raw.githubusercontent.com/sudosubin/setup-script/master/OneDark.colorscheme > ~/.local/share/konsole/OneDark.colorscheme
  # kwriteconfig5 --file konsolerc --group "Desktop Entry" --key DefaultProfile "Profile 1.profile"
  # kwriteconfig5 --file ~/.local/share/konsole/Profile\ 1.profile --group General --key Name "Profile 1"
  # kwriteconfig5 --file ~/.local/share/konsole/Profile\ 1.profile --group Appearance --key ColorScheme "OneDark"
  # kwriteconfig5 --file ~/.local/share/konsole/Profile\ 1.profile --group "Cursor Options" --key CursorShape 1
  # kwriteconfig5 --file ~/.local/share/konsole/Profile\ 1.profile --group General --key TerminalCenter true
  # kwriteconfig5 --file ~/.local/share/konsole/Profile\ 1.profile --group General --key TerminalMargin 1

  # Configure power
  msg_step "Configure power"
  msg_normal "change power settings, idle time"
  kwriteconfig5 --file powermanagementprofilesrc \
    --group AC --group DimDisplay \
    --key idleTime 1800000
  kwriteconfig5 --file powermanagementprofilesrc \
    --group AC --group DPMSControl \
    --key idleTime 1800

  # Configure dolphin
  msg_step "Configure dolphin"

  kwriteconfig5 --file dolphinrc --group General \
    --key ShowFullPath true
  kwriteconfig5 --file dolphinrc --group General \
    --key ShowFullPathInTitlebar true
  kwriteconfig5 --file dolphinrc --group General \
    --key ShowSpaceInfo false
  kwriteconfig5 --file dolphinrc --group General \
    --key ShowToolTips true
  kwriteconfig5 --file dolphinrc --group General \
    --key ShowZoomSlider false

  kwriteconfig5 --file dolphinrc --group DetailsMode \
    --key PreviewSize 16

  kwriteconfig5 --file dolphinrc --group "Toolbar mainToolBar" \
    --key ToolButtonStyle "IconOnly"

  kwriteconfig5 --file dolphinrc \
    --group MainWindow --group "Toolbar mainToolBar" \
    --key ToolButtonStyle "IconOnly"
}
