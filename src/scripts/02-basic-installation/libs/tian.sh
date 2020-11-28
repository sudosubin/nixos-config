#!/bin/bash

install_tian() {
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

  # Configure tian
  msg_step "Configure tian"

  # make tian default input method
  msg_normal "make tian default input method"
  echo "[ -f /etc/input.d/tian.conf ] && . /etc/input.d/tian.conf" \
    | silent tee "$HOME/.xinputrc"

  # configure tian keys
  msg_normal "configure tian keys"

  local hangul_keys="['Hangul', 'Alt_R']"
  local hanja_keys="['Hangul_Hanja', 'Control_R']"
  local xkb_option_ctrl="'ctrl:menu_rctrl', 'ctrl:swapcaps'"
  local xkb_option_korean="'korean:ralt_hangul', 'korean:rctrl_hanja'"
  local xkb_options="[$xkb_option_ctrl, $xkb_option_korean]"

  gsettings set com.nimfsoft.tian setup-environment-variables true
  gsettings set com.nimfsoft.tian hotkeys "$hangul_keys"
  gsettings set com.nimfsoft.tian.inputs.gtk hook-key-events true
  gsettings set com.nimfsoft.tian.settings xkb-options "$xkb_options"

  gsettings set com.nimfsoft.tian.linguas.tian-korean hanja-keys "$hanja_keys"
  gsettings set com.nimfsoft.tian.linguas.tian-korean shortcuts-to-sys "$hangul_keys"
  gsettings set com.nimfsoft.tian.linguas.tian-korean shortcuts-to-lang "$hangul_keys"
  gsettings set com.nimfsoft.tian.linguas.tian-korean activate-lingua true

  # disable unused languages
  gsettings set com.nimfsoft.tian.linguas.tian-rime activate-lingua false
  gsettings set com.nimfsoft.tian.linguas.tian-anthy activate-lingua false
  gsettings set com.nimfsoft.tian.linguas.tian-m17n-vi activate-lingua false
}
