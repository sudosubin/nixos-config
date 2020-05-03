#!/bin/bash

set_colors() {
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

  # Set colors: One Dark
  msg_step "Set colors: One Dark"

  # copy to colors directory
  local kde_dir
  local local_dir
  local origin_dir

  kde_dir="$HOME/.kde/share/apps/color-schemes"
  local_dir="$HOME/.local/share/color-schemes"
  origin_dir="$script_dir/assets/OneDark.colors"

  mkdir -p "$kde_dir"
  cp "$origin_dir" "$kde_dir"

  mkdir -p "$local_dir"
  cp "$origin_dir" "$local_dir"

  # copy all keys from color to kdeglobals
  msg_step "Copy colors to kdeglobals"

  while IFS= read -r line; do
    if [[ $line = \[* ]]; then
      # Group
      group=${line:1:-1}
    elif [[ $line = [a-zA-Z]* ]]; then
      # Key, value
      key=$(echo "$line" | cut -d'=' -f 1)
      value=$(echo "$line" | cut -d'=' -f 2)

      # write value in loop
      kwriteconfig5 --file kdeglobals --group "$group" \
        --key "$key" "$value"
      kwriteconfig5 --file ~/.kde/share/config/kdeglobals --group "$group" \
        --key "$key" "$value"
    fi
  done < "$origin_dir"

  # set ColorScheme
  kwriteconfig5 --file kdeglobals --group General --key ColorScheme "OneDark"
}
