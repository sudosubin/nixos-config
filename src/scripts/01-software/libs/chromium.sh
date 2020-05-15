#!/bin/bash

add_ppa_chromium() {
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

  # Add ppa: saiarcot895/chromium-dev
  msg_step "Add ppa: saiarcot895/chromium-dev"

  # add apt repository
  msg_normal "add apt repository"
  sudo add-apt-repository -ny ppa:saiarcot895/chromium-dev

  # add Google api key
  msg_normal "add Google api key"
  cp "$script_dir/keys/google-api-key" ~/.zprofile

  # add apt hooks
  msg_normal "add apt hooks (dark mode)"
  sudo cp "$script_dir/hooks/chromium-upgrade-helper" \
    /usr/local/bin/chromium-upgrade-helper
  sudo chmod 777 /usr/local/bin/chromium-upgrade-helper
  echo 'DPkg::Post-Invoke {"/usr/local/bin/chromium-upgrade-helper";};' \
    | silent sudo tee /etc/apt/apt.conf.d/80upgradehook
}
