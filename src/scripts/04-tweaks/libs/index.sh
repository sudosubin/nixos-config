#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=keyboard_and_mouse.sh
source "$script_dir/libs/keyboard_and_mouse.sh"

# shellcheck source=plasma-etc.sh
source "$script_dir/libs/plasma-etc.sh"

# shellcheck source=workspace-behaviors.sh
source "$script_dir/libs/workspace-behaviors.sh"

# shellcheck source=window-management.sh
source "$script_dir/libs/window-management.sh"
