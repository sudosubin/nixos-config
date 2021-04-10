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

# shellcheck source=vscodium.sh
source "$script_dir/libs/vscodium.sh"

# alacritty
add_ppa_alacritty() {
  # Add ppa: aslatter/ppa
  msg_step "Add ppa: aslatter/ppa"
  sudo add-apt-repository -ny ppa:aslatter/ppa
}

# ulauncher
add_ppa_ulauncher() {
  # Add ppa: agornostal/ulauncher
  msg_step "Add ppa: agornostal/ulauncher"
  sudo add-apt-repository -ny ppa:agornostal/ulauncher
}

# git
add_ppa_git() {
  # Add ppa: git
  msg_step "Add ppa: git"
  sudo add-apt-repository -ny ppa:git-core/ppa
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

# slack
add_ppa_spotify() {
  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  script_dir="$(dirname "$current_dir")"
  app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

  # shellcheck source=../../../../src/utils/ppa.sh
  source "$app_dir/src/utils/ppa.sh"

  msg_step "Add ppa: spotify"

  local spotify_download="https://download.spotify.com/debian"
  local spotify_repo="http://repository.spotify.com"

  add_ppa slack \
    "$spotify_download/pubkey_0D811D58.gpg" \
    "deb $spotify_repo stable non-free"
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
