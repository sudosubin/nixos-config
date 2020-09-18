#!/bin/bash

set_keyboard_and_mouse() {
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

  # Configure keyboard
  msg_step "Configure keyboard"

  msg_normal "set xkbmap"
  sudo cp "$script_dir/settings/00-keyboard.conf" \
    "/usr/share/X11/xorg.conf.d/00-keyboard.conf"
  # setxkbmap -option \
  #   "ctrl:menu_rctrl,ctrl:swapcaps,korean:ralt_hangul,korean:rctrl_hanja"

  msg_normal "set global shortcuts"
  kwriteconfig5 --file kglobalshortcutsrc --group kwin \
    --key "Window Close" "Alt+F4\tAlt+Esc,Alt+F4,Close Window"
  kwriteconfig5 --file kglobalshortcutsrc --group kwin \
    --key "next activity" ",none,Walk through activities"
  kwriteconfig5 --file kglobalshortcutsrc --group plasmashell \
    --key "next activity" ",none,Walk through activities"
  kwriteconfig5 --file kglobalshortcutsrc --group kwin \
    --key "ShowDesktopGrid" "Meta+Tab,Ctrl+F8,Show Desktop Grid"
  kwriteconfig5 --file kglobalshortcutsrc --group kwin \
    --key "Expose" \
    "Meta+\`,Ctrl+F9,Toggle Present Windows (Current desktop)"
  kwriteconfig5 --file kglobalshortcutsrc --group kwin \
    --key "Switch One Desktop to the Left" \
    "Ctrl+Alt+Left,Meta+Ctrl+Left,Switch One Desktop to the Left"
  kwriteconfig5 --file kglobalshortcutsrc --group kwin \
    --key "Switch One Desktop to the Right" \
    "Ctrl+Alt+Right,Meta+Ctrl+Right,Switch One Desktop to the Right"
  kwriteconfig5 --file kglobalshortcutsrc --group kwin \
    --key "Window to Next Desktop" \
    "Ctrl+Alt+Shift+Right,none,Window to Next Desktop"
  kwriteconfig5 --file kglobalshortcutsrc --group kwin \
    --key "Window to Previous Desktop" \
    "Ctrl+Alt+Shift+Left,none,Window to Previous Desktop"

  # replace \\t to \t
  sed -i 's|\\\\t|\\t|g' ~/.config/kglobalshortcutsrc

  msg_normal "set keyboard repeat delay"
  kwriteconfig5 --file kcminputrc --group Keyboard --key RepeatDelay 250
  kwriteconfig5 --file kcminputrc --group Keyboard --key RepeatRate 40

  # Configure mouse
  msg_step "Configure mouse"

  msg_normal "change scroll direction, cursor speed"
  kwriteconfig5 --file kcminputrc --group Mouse \
    --key XLbInptNaturalScroll false
  kwriteconfig5 --file kcminputrc --group Mouse \
    --key XLbInptPointerAcceleration 0.6
}
