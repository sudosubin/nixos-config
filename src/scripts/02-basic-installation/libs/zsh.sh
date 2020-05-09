#!/bin/bash

install_zsh() {
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

  # Install zsh
  msg_step "Configure zsh & zinit"

  # zsh as default shell
  msg_normal "make zsh as default shell"

  local pam_required="required   pam_shells.so"
  local pam_sufficient="sufficient   pam_shells.so"

  sudo sed -iE "s/$pam_required/$pam_sufficient/g" /etc/pam.d/chsh
  chsh -s "$(command -v zsh)"
  sudo sed -iE "s/$pam_sufficient/$pam_required/g" /etc/pam.d/chsh

  # install zinit
  msg_normal "install zinit from git"
  mute git clone https://github.com/zdharma/zinit.git ~/.zinit/bin

  # copy zsh settigns
  msg_normal "copy .zshrc, .zshenv"
  cp "$script_dir/settings/.zshrc" ~/.zshrc
  cp "$script_dir/settings/.zshenv" ~/.zshenv
  cp "$script_dir/settings/.p10k.zsh" ~/.p10k.zsh
}
