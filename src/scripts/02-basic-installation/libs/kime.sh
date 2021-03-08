#!/bin/bash

install_kime() {
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

  # Install kime
  msg_step "Install kime"

  # downlaod kime
  msg_normal "download kime from github release"
  curl -sL \
    https://github.com/Riey/kime/releases/download/v1.3.1/kime_ubuntu-20.04_v1.3.1_amd64.deb \
    -o kime.deb

  # install kime
  msg_normal "install kime"
  silent sudo dpkg -i kime.deb

  # # configure nimf keys
  # msg_normal "configure nimf keys"

  # local hangul_keys="['Hangul', 'Alt_R']"
  # local hanja_keys="['Hangul_Hanja', 'Control_R']"
  # local xkb_option_ctrl="'ctrl:menu_rctrl', 'ctrl:swapcaps'"
  # local xkb_option_korean="'korean:ralt_hangul', 'korean:rctrl_hanja'"
  # local xkb_options="[$xkb_option_ctrl, $xkb_option_korean]"

  # gsettings set org.nimf setup-environment-variables true
  # gsettings set org.nimf hotkeys "$hangul_keys"
  # gsettings set org.nimf.clients.gtk hook-gdk-event-key true
  # gsettings set org.nimf.clients.gtk reset-on-gdk-button-press-event false
  # gsettings set org.nimf.settings xkb-options "$xkb_options"
  # gsettings set org.nimf.engines.nimf-libhangul shortcuts-to-sys "$hangul_keys"
  # gsettings set org.nimf.engines.nimf-libhangul shortcuts-to-lang "$hangul_keys"
  # gsettings set org.nimf.engines.nimf-libhangul hanja-keys "$hanja_keys"

  # clean up
  msg_normal "clean up"
  rm -rf kime.deb
}
