# Snippets

Copy and paste this codes easily.

## Specify bash script

```sh
#!/bin/bash
```

Add this line to top of the file.

## Directory

```sh
# in ./<file>.sh
APP_DIR="$(dirname "$(readlink -fm "$0")")"

# in ./src/scripts/<file>.sh
CURRENT_DIR="$(dirname "${BASH_SOURCE[0]}")"
APP_DIR="$(dirname "$(dirname "$(dirname "$CURRENT_DIR")")")"

# in ./src/scripts/<1-dep>/<file>.sh
CURRENT_DIR="$(dirname "${BASH_SOURCE[0]}")"
APP_DIR="$(dirname "$(dirname "$(dirname "$(dirname "$CURRENT_DIR")")")")"
```

## Import function

```sh
source "$APP_DIR/src/utils/echo.sh"
source "$APP_DIR/src/utils/stdout.sh"
```
