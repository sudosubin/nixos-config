{
  config,
  lib,
  pkgs,
  ...
}:

{
  services.caffeinate = {
    enable = true;
    args = "-d";
  };
}
