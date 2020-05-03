#!/bin/bash

# Silent (stdout)
function silent {
  "$@" > /dev/null
}

# Mute (stdout, stderr)
function mute {
  "$@" &> /dev/null
}
