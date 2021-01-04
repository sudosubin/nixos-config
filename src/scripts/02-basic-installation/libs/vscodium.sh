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
    # theme
    timeout 10 codium --install-extension zhuangtongfa.Material-theme
    timeout 10 codium --install-extension PKief.material-icon-theme
    timeout 10 codium --install-extension iocave.customize-ui

    # language (python)
    timeout 10 codium --install-extension ms-python.python
    timeout 10 codium --install-extension ms-pyright.pyright

    # language (javascript)
    timeout 10 codium --install-extension dbaeumer.vscode-eslint
    timeout 10 codium --install-extension esbenp.prettier-vscode
    timeout 10 codium --install-extension jpoissonnier.vscode-styled-components

    # language (java)
    timeout 10 codium --install-extension redhat.java
    timeout 10 codium --install-extension mathiasfrohlich.kotlin

    # language (bash)
    timeout 10 codium --install-extension timonwong.shellcheck
    timeout 10 codium --install-extension exiasr.hadolint

    # language (etc)
    timeout 10 codium --install-extension bungcip.better-toml
    timeout 10 codium --install-extension aaron-bond.better-comments

    # etc
    timeout 10 codium --install-extension eamodio.gitlens
    timeout 10 codium --install-extension shardulm94.trailing-spaces
    timeout 10 codium --install-extension yzhang.markdown-all-in-one
  } | output_box cat
}
