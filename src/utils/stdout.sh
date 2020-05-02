#!/bin/bash

# Mute
## Mute > Silent (stdout)
function silent {
  $@ >/dev/null
}

## Mute > Mute (stdout, stderr)
function mute {
  $@ &>/dev/null
}
