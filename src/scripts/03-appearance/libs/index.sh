#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=colors.sh
source "$script_dir/libs/colors.sh"

# shellcheck source=cursors.sh
source "$script_dir/libs/cursors.sh"

# shellcheck source=fonts.sh
source "$script_dir/libs/fonts.sh"

# shellcheck source=icons.sh
source "$script_dir/libs/icons.sh"

# shellcheck source=global-theme.sh
source "$script_dir/libs/global-theme.sh"

# shellcheck source=latte.sh
source "$script_dir/libs/latte.sh"

# shellcheck source=wallpaper.sh
source "$script_dir/libs/wallpaper.sh"

# shellcheck source=window-decorations.sh
source "$script_dir/libs/window-decorations.sh"
