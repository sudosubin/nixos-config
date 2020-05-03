#!/bin/bash

# Silent (stdout)
silent() {
  "$@" > /dev/null
}

# Mute (stdout, stderr)
mute() {
  "$@" &> /dev/null
}
