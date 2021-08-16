#!/usr/bin/env sh

export "$(gnome-keyring-daemon --start --components=pkcs11,secrets,ssh)"
