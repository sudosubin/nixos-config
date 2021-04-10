#!/bin/bash

scripts_05() {
  # Directory
  local current_dir
  local app_dir
  local settings_dir

  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  app_dir="$(dirname "$(dirname "$(dirname "$current_dir")")")"
  settings_dir="$app_dir/src/scripts/05-additional-installation/settings"

  # Function
  # shellcheck source=../../../src/utils/msg.sh
  source "$app_dir/src/utils/msg.sh"
  # shellcheck source=../../../src/utils/stdout.sh
  source "$app_dir/src/utils/stdout.sh"
  # shellcheck source=libs/index.sh
  source "$current_dir/libs/index.sh"

  # 05. Additional Installation (for development)
  msg_title "05. Additional Installation (for development)"

  # Install requirements
  msg_heading "Install requirements"
  msg_normal "install"
  output_box sudo apt-get -y --no-install-recommends install \
    build-essential libssl-dev zlib1g-dev libbz2-dev libjpeg8-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
    libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl \
    libmysqlclient-dev libpq-dev python3-venv \
    libcurl4-openssl-dev libssl-dev libaec-dev \
    dirmngr gpg \
    docker.io docker-compose redis-server insomnia shellcheck jq \
    watchman gh

  msg_normal "fix Mysql-python my_config.h error"
  sudo curl -s "https://raw.githubusercontent.com/paulfitz/\
mysql-connector-c/master/include/my_config.h" -o /usr/include/mysql/my_config.h

  # Install dotfiles
  git clone --bare https://github.com/sudosubin/dotfiles.git ~/.cfg
  git --git-dir="$HOME/.cfg/" --work-tree="$HOME" checkout -f
  git --git-dir="$HOME/.cfg/" --work-tree="$HOME" submodule update --init
  git --git-dir="$HOME/.cfg/" --work-tree="$HOME" submodule foreach -q \
    --recursive 'git checkout $(git config -f $toplevel/.gitmodules submodule.$name.branch || echo master)'

  # Install AWS CLI
  msg_heading "Install AWS CLI"
  install_awscli

  # Install asdf-vm plugins
  msg_heading "Install asdf-vm plugins"
  install_asdf

  # Install poetry
  msg_heading "Install poetry"
  install_poetry

  # Change max fs watch
  msg_heading "Change max fs watch limit"
  echo "fs.inotify.max_user_watches=524288" \
    | silent sudo tee -a /etc/sysctl.conf

  # Add docker to sudo group
  msg_heading "Add docker to sudo group"
  sudo usermod -aG docker "$USER"
}
