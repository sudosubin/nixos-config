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
  local kde_dir="$HOME/.kde/share/apps/color-schemes"
  local local_dir="$HOME/.local/share/color-schemes"
  local origin_dir="$script_dir/assets/OneDark.colors"
  local chromium_dir="$script_dir/assets/OneDarkChromium.colors"

  mkdir -p "$kde_dir"
  cp "$origin_dir" "$kde_dir"
  cp "$chromium_dir" "$kde_dir"

  mkdir -p "$local_dir"
  cp "$origin_dir" "$local_dir"
  cp "$chromium_dir" "$local_dir"

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

  # Set ColorScheme
  kwriteconfig5 --file kdeglobals --group General --key ColorScheme "OneDark"

  # window rules
  kwriteconfig5 --file kwinrulesrc --group General --key count 2

  # Set ColorScheme per Application
  kwriteconfig5 --file kwinrulesrc --group 1 --key Description \
    "Application settings for chromium"
  kwriteconfig5 --file kwinrulesrc --group 1 --key clientmachine \
    "localhost"
  kwriteconfig5 --file kwinrulesrc --group 1 --key clientmachinematch 0
  kwriteconfig5 --file kwinrulesrc --group 1 --key wmclass \
    "chromium"
  kwriteconfig5 --file kwinrulesrc --group 1 --key wmclasscomplete false
  kwriteconfig5 --file kwinrulesrc --group 1 --key wmclassmatch 1
  kwriteconfig5 --file kwinrulesrc --group 1 --key decocolorrule 2
  kwriteconfig5 --file kwinrulesrc --group 1 --key decocolor \
    "OneDarkChromium"

  # Set st-term window size
  kwriteconfig5 --file kwinrulesrc --group 2 --key Description \
    "Application settings for st"
  kwriteconfig5 --file kwinrulesrc --group 2 --key clientmachine \
    "localhost"
  kwriteconfig5 --file kwinrulesrc --group 2 --key clientmachinematch 0
  kwriteconfig5 --file kwinrulesrc --group 2 --key wmclass \
    "st"
  kwriteconfig5 --file kwinrulesrc --group 2 --key wmclasscomplete false
  kwriteconfig5 --file kwinrulesrc --group 2 --key wmclassmatch 1
  kwriteconfig5 --file kwinrulesrc --group 2 --key size "800,500"
  kwriteconfig5 --file kwinrulesrc --group 2 --key sizerule 3
}