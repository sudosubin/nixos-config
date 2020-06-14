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

  # Delta git-diff
  git config --global interactive.diffFilter "delta --color-only"
  git config --global core.pager \
    "delta \
--max-line-distance 1 --theme=base16 --24-bit-color=always \
--file-color=#08000000 \
--hunk-color=#08000000 \
--minus-color=#400000 --minus-emph-color=#600000 \
--plus-color=#003000 --plus-emph-color=#005000"
}