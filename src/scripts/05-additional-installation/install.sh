#!/bin/bash

scripts_05() {
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

  # 05. Additional Installation (for development)
  msg_title "05. Additional Installation (for development)"

  # Install requirements
  msg_heading "Install requirements"
  msg_normal "install"
  output_box sudo apt-get -y --no-install-recommends install \
    build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
    libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl \
    libmysqlclient-dev libpq-dev \
    dirmngr gpg \
    shellcheck jq

  msg_normal "fix Mysql-python my_config.h error"
  sudo curl -s "https://raw.githubusercontent.com/paulfitz/\
mysql-connector-c/master/include/my_config.h" -o /usr/include/mysql/my_config.h

  # Install AWS CLI
  msg_heading "Install AWS CLI"
  install_awscli

  # Install asdf-vm plugins
  msg_heading "Install asdf-vm plugins"
  install_asdf
}
