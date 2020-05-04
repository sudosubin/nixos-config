#!/bin/bash

set_plasma_etc() {
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

  # Configure locale
  msg_step "Configure locale"
  msg_normal "change locale to en_US.UTF-8"
  kwriteconfig5 --file plasma-localerc --group Formats --key useDetailed true
  kwriteconfig5 --file plasma-localerc --group Formats \
    --key LC_TIME "en_US.UTF-8"
  
  # Configure krunner
  msg_step "Configure krunner"
  msg_normal "change krunner to float on center"
  kwriteconfig5 --file krunnerrc --group General --key FreeFloating true

  # Configure Power
  msg_step "Configure Power"
  msg_normal "change power settings, idle time"
  kwriteconfig5 --file powermanagementprofilesrc \
    --group AC --group DimDisplay \
    --key idleTime 1800000
  kwriteconfig5 --file powermanagementprofilesrc \
    --group AC --group DPMSControl \
    --key idleTime 1800
}
