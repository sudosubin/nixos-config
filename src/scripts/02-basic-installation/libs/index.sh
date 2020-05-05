#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=requirements.sh
source "$script_dir/libs/requirements.sh"

# shellcheck source=alacritty.sh
source "$script_dir/libs/alacritty.sh"

# shellcheck source=asdf.sh
source "$script_dir/libs/asdf.sh"

# shellcheck source=capitaine-cursors.sh
source "$script_dir/libs/capitaine-cursors.sh"

# shellcheck source=hello.sh
source "$script_dir/libs/hello.sh"

# shellcheck source=la-capitaine-icon-theme.sh
source "$script_dir/libs/la-capitaine-icon-theme.sh"

# shellcheck source=latte.sh
source "$script_dir/libs/latte.sh"

# shellcheck source=nimf.sh
source "$script_dir/libs/nimf.sh"

# shellcheck source=ulauncher.sh
source "$script_dir/libs/ulauncher.sh"

# shellcheck source=vscodium.sh
source "$script_dir/libs/vscodium.sh"

# shellcheck source=zsh.sh
source "$script_dir/libs/zsh.sh"
