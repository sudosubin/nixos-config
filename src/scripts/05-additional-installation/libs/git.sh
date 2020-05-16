#!/bin/bash

install_git() {
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

  # Default git hooks
  msg_step "Default git hooks"

  msg_normal "jira commit msg hooks"
  mkdir -p ~/.git-config/hooks
  cp "$script_dir/settings/commit-msg" "$HOME/.git-config/hooks/commit-msg"
  chmod +x "$HOME/.git-config/hooks/commit-msg"

  git config --global core.hookspath "$HOME/.git-config/hooks"
}
