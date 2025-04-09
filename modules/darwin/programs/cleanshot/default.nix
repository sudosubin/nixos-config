{
  config,
  lib,
  pkgs,
  ...
}:

{
  services.cleanshot = {
    enable = true;
  };
}
