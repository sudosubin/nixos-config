#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=asdf.sh
source "$script_dir/libs/asdf.sh"

# shellcheck source=awscli.sh
source "$script_dir/libs/awscli.sh"

# shellcheck source=poetry.sh
source "$script_dir/libs/poetry.sh"
