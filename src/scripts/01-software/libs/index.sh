#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=insomnia.sh
source "$script_dir/libs/insomnia.sh"

# shellcheck source=jetbrains.sh
source "$script_dir/libs/jetbrains.sh"

# shellcheck source=vscode.sh
source "$script_dir/libs/vscode.sh"

# ulauncher
add_ppa_ulauncher() {
  # Add ppa: agornostal/ulauncher
  msg_step "Add ppa: agornostal/ulauncher"
  sudo add-apt-repository -ny ppa:agornostal/ulauncher
}

# applet-window-buttons
add_ppa_applet_window_buttons() {
  # Add ppa: krisives/applet-window-buttons
  msg_step "Add ppa: krisives/applet-window-buttons"
  sudo add-apt-repository -ny ppa:krisives/applet-window-buttons
}

# keepassxc
add_ppa_keepassxc() {
  # Add ppa: keepassxc
  msg_step "Add ppa: keepassxc"
  sudo add-apt-repository -ny ppa:phoerious/keepassxc
}

# nimf
add_ppa_nimf() {
  # Add ppa: nemonein/nimf
  msg_step "Add ppa: nemonein/nimf"
  sudo add-apt-repository -ny ppa:nemonein/nimf
}

# github cli
add_ppa_github_cli() {
  # Add ppa: github cli
  msg_step "Add ppa: github cli"
  sudo apt-key adv --keyserver keyserver.ubuntu.com \
    --recv-key C99B11DEB97541F0
  sudo apt-add-repository -ny https://cli.github.com/packages
}

# chrome
add_ppa_chrome() {
  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  script_dir="$(dirname "$current_dir")"
  app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

  # shellcheck source=../../../../src/utils/ppa.sh
  source "$app_dir/src/utils/ppa.sh"

  # Add ppa: chrome
  msg_step "Add ppa: chrome"

  local chrome_repo="https://dl.google.com/linux"

  add_ppa google-chrome \
    "$chrome_repo/linux_signing_key.pub" \
    "deb [arch=amd64] $chrome_repo/chrome/deb/ stable main"

  # Add upgrade hook
  sudo cp "$script_dir/hooks/chrome-upgrade-helper" \
    /usr/local/bin/chrome-upgrade-helper
  sudo chmod 777 /usr/local/bin/chrome-upgrade-helper
  echo 'DPkg::Post-Invoke {"/usr/local/bin/chrome-upgrade-helper";};' \
    | silent sudo tee /etc/apt/apt.conf.d/80upgradehook
}

# slack
add_ppa_slack() {
  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  script_dir="$(dirname "$current_dir")"
  app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

  # shellcheck source=../../../../src/utils/ppa.sh
  source "$app_dir/src/utils/ppa.sh"

  msg_step "Add ppa: slack"

  local slack_repo="https://packagecloud.io/slacktechnologies/slack"

  add_ppa slack \
    "$slack_repo/gpgkey" \
    "deb $slack_repo/debian/ jessie main"
}

# yarn
add_ppa_yarn() {
  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  script_dir="$(dirname "$current_dir")"
  app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

  # shellcheck source=../../../../src/utils/ppa.sh
  source "$app_dir/src/utils/ppa.sh"

  # Add ppa: yarn
  msg_step "Add ppa: yarn"

  local yarn_repo="https://dl.yarnpkg.com"

  add_ppa yarn \
    "$yarn_repo/debian/pubkey.gpg" \
    "deb $yarn_repo/debian/ stable main"
}
