# shellcheck shell=bash

wrapFHSEnvironment() {
  local prog="$1"
  local dest="$2"
  local hidden

  assertExecutable "$prog"

  hidden="$(dirname "$prog")/.$(basename "$prog")"-wrapped
  while [ -e "$hidden" ]; do
    hidden="${hidden}_"
  done
  mv "$prog" "$hidden"

  # shellcheck disable=SC1078,SC1079,SC2016
  printf '''#!@shell@ -e

dest="%s"
hidden="%s"

sha() {
  @sha256sum@ "$1" | cut -d" " -f1
}

if [ ! -f "$(dirname "$dest")" ]; then
  sudo mkdir -p "$(dirname "$dest")"
fi

if [ ! -f "$dest" ] || [ "$(sha "$hidden")" != "$(sha "$dest")" ]; then
  sudo cp "$hidden" "$dest"
fi

exec -a "$0" "$dest" "$@"''' "$dest" "$hidden" > "$prog"

  chmod +x "$prog"
}
