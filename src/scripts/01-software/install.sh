#!/bin/bash

scripts_01() {
  # Directory
  local current_dir
  local app_dir

  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  app_dir="$(dirname "$(dirname "$(dirname "$current_dir")")")"

  # Function
  # shellcheck source=../../../src/utils/msg.sh
  source "$app_dir/src/utils/msg.sh"
  # shellcheck source=../../../src/utils/stdout.sh
  source "$app_dir/src/utils/stdout.sh"
  # shellcheck source=libs/index.sh
  source "$current_dir/libs/index.sh"

  # 01. Software
  msg_title "01. Software"

  # Change software sources mirror
  msg_heading "Change software sources mirror"

  msg_step "Change from ubuntu to kakao"
  sudo sed -i -Ee "s|[a-z]{2}.archive.ubuntu.com|archive.ubuntu.com|g" \
    -e "s|archive.ubuntu.com|mirror.kakao.com|g" /etc/apt/sources.list

  # Update & Upgrade packages
  msg_heading "Update & upgrade packages"

  msg_step "Update packages"
  output_box sudo apt-get update

  msg_step "Upgrade packages"
  output_box sudo apt-get -y upgrade

  # Add packages ppa
  msg_heading "Add packages ppa"

  add_ppa_alacritty
  add_ppa_chrome
  add_ppa_insomnia
  add_ppa_jetbrains
  add_ppa_github_cli
  add_ppa_slack
  add_ppa_spotify
  add_ppa_vscodium
  add_ppa_yarn

  # Add upgrade hook
  msg_heading "Add upgrade hook"
  sudo cp "$current_dir/hooks/upgrade-helper" \
    /usr/local/bin/upgrade-helper
  echo 'DPkg::Post-Invoke {"/usr/local/bin/upgrade-helper";};' \
    | silent sudo tee /etc/apt/apt.conf.d/80upgradehook
}
