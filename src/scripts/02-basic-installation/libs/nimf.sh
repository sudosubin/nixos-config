#!/bin/bash

install_nimf() {
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

  # Configure  nimf
  msg_step "Configure nimf"

  # make nimf default input method
  msg_normal "make nimf default input method"
  im-config -n nimf

  # configure nimf keys
  msg_normal "configure nimf keys"

  local hangul_keys
  local hanja_keys
  local xkb_option_ctrl
  local xkb_option_korean
  local xkb_options

  hangul_keys="['Hangul', 'Alt_R']"
  hanja_keys="['Hangul_Hanja', 'Control_R']"
  xkb_option_ctrl="'ctrl:menu_rctrl', 'ctrl:swapcaps'"
  xkb_option_korean="'korean:ralt_hangul', 'korean:rctrl_hanja'"
  xkb_options="[$xkb_option_ctrl, $xkb_option_korean]"

  gsettings set org.nimf setup-environment-variables true
  gsettings set org.nimf hotkeys "$hangul_keys"
  gsettings set org.nimf.clients.gtk hook-gdk-event-key true
  gsettings set org.nimf.clients.gtk reset-on-gdk-button-press-event false
  gsettings set org.nimf.settings xkb-options "$xkb_options"
  gsettings set org.nimf.engines.nimf-libhangul shortcuts-to-sys "$hangul_keys"
  gsettings set org.nimf.engines.nimf-libhangul shortcuts-to-lang "$hangul_keys"
  gsettings set org.nimf.engines.nimf-libhangul hanja-keys "$hanja_keys"
}
