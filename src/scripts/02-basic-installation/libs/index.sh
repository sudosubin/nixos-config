#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=requirements.sh
source "$script_dir/libs/requirements.sh"

# shellcheck source=bloats.sh
source "$script_dir/libs/bloats.sh"

# shellcheck source=kime.sh
source "$script_dir/libs/kime.sh"

# shellcheck source=la-capitaine-icon-theme.sh
source "$script_dir/libs/la-capitaine-icon-theme.sh"

# shellcheck source=vscodium.sh
source "$script_dir/libs/vscodium.sh"

# shellcheck source=zsh.sh
source "$script_dir/libs/zsh.sh"
