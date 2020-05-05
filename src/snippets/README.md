# Snippets

Copy and paste below easily.

## Specify bash script

```sh
#!/bin/bash
```

Add this line to top of the file.

## Directory

```sh
# in ./<file>.sh
local app_dir

app_dir="$(dirname "$(readlink -fm "$0")")"

# in ./src/scripts/00-directory/<file>.sh
local current_dir
local app_dir

current_dir="$(dirname "${BASH_SOURCE[0]}")"
app_dir="$(dirname "$(dirname "$(dirname "$CURRENT_DIR")")")"

# in ./src/scripts/00-directory/<1-dep>/<file>.sh
local current_dir
local script_dir
local app_dir

current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"
```

## Import function

```sh
source "$APP_DIR/src/utils/echo.sh"
source "$APP_DIR/src/utils/stdout.sh"
```
