#!/bin/bash

install_vscodium() {
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

  # Configure vscodium
  msg_step "Configure vscodium"

  # install vscodium extensions
  msg_normal "install vscodium extensions (takes long time)"
  {
    codium --install-extension zhuangtongfa.Material-theme
    codium --install-extension PKief.material-icon-theme
    codium --install-extension ms-python.python
    codium --install-extension ms-python.vscode-pylance
    codium --install-extension njpwerner.autodocstring
    codium --install-extension fabiospampinato.vscode-highlight
    codium --install-extension timonwong.shellcheck
    codium --install-extension mrorz.language-gettext
    codium --install-extension eamodio.gitlens
    codium --install-extension shardulm94.trailing-spaces
    codium --install-extension iocave.customize-ui
    codium --install-extension bungcip.better-toml
  } | output_box cat

  # configure vscodium settings
  msg_normal "configure vscodium settings"
  cp "$script_dir/settings/vscodium.json" ~/.config/VSCodium/User/settings.json
}
