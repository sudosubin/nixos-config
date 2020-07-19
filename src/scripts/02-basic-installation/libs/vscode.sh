#!/bin/bash

install_vscode() {
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

  # Configure vscode
  msg_step "Configure vscode"

  # install vscode extensions
  msg_normal "install vscode extensions (takes long time)"
  {
    code --install-extension zhuangtongfa.Material-theme
    code --install-extension PKief.material-icon-theme
    code --install-extension ms-python.python
    code --install-extension ms-python.vscode-pylance
    code --install-extension njpwerner.autodocstring
    code --install-extension fabiospampinato.vscode-highlight
    code --install-extension timonwong.shellcheck
    code --install-extension mrorz.language-gettext
    code --install-extension eamodio.gitlens
    code --install-extension shardulm94.trailing-spaces
    code --install-extension iocave.customize-ui
    code --install-extension bungcip.better-toml
    code --install-extension yzhang.markdown-all-in-one
  } | output_box cat

  # configure vscode settings
  msg_normal "configure vscode settings"
  cp "$script_dir/settings/vscode.json" ~/.config/Code/User/settings.json
}
