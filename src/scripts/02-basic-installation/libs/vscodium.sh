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
  # - zhuangtongfa.Material-theme: One Dark Pro Theme
  # - PKief.material-icon-theme: Material Icon Theme
  # - ms-python.python: Python Language support
  # - timonwong.shellcheck: Bash style checker
  # - mrorz.language-gettext: gettext(.po) Syntax support
  # - GitHub.vscode-pull-request-github: GitHub PR from codium
  # - eamodio.gitlens: Git blame in codium
  msg_normal "install vscodium extensions (takes long time)"
  {
    codium --install-extension zhuangtongfa.Material-theme
    codium --install-extension PKief.material-icon-theme
    codium --install-extension ms-python.python
    codium --install-extension timonwong.shellcheck
    codium --install-extension mrorz.language-gettext
    codium --install-extension GitHub.vscode-pull-request-github
    codium --install-extension eamodio.gitlens
    codium --install-extension shardulm94.trailing-spaces
  } | output_box cat

  # configure vscodium settings
  msg_normal "configure vscodium settings"
  cp "$script_dir/settings/vscodium.json" ~/.config/VSCodium/User/settings.json
}
