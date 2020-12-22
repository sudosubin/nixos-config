#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=chromium.sh
source "$script_dir/libs/chromium.sh"

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

# github cli
add_ppa_github_cli() {
  # Add ppa: github cli
  msg_step "Add ppa: github cli"
  sudo apt-key adv --keyserver keyserver.ubuntu.com \
    --recv-key C99B11DEB97541F0
  sudo apt-add-repository -ny https://cli.github.com/packages
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

# nimf
add_ppa_nimf() {
  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  script_dir="$(dirname "$current_dir")"
  app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

  # shellcheck source=../../../../src/utils/ppa.sh
  source "$app_dir/src/utils/ppa.sh"

  msg_step "Add ppa: nimf"

  add_ppa "hamonikr-pkg" \
    "https://pkg.hamonikr.org/hamonikr-pkg.key" \
    "deb [arch=amd64] https://pkg.hamonikr.org focal main"
}

# spotify
add_ppa_spotify() {
  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  script_dir="$(dirname "$current_dir")"
  app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

  # shellcheck source=../../../../src/utils/ppa.sh
  source "$app_dir/src/utils/ppa.sh"

  # Add ppa: spotify
  msg_step "Add ppa: spotify"

  add_ppa spotify \
    "https://download.spotify.com/debian/pubkey_0D811D58.gpg" \
    "deb http://repository.spotify.com stable non-free"
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
