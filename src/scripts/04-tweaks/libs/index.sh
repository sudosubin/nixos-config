#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=auto-login.sh
source "$script_dir/libs/auto-login.sh"

# shellcheck source=network.sh
source "$script_dir/libs/network.sh"
