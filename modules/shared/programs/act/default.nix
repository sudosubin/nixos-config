{
  config,
  pkgs,
  lib,
  ...
}:
with lib;

{
  programs.act = {
    enable = true;
    config = {
      platform = {
        "ubuntu-latest" = "ghcr.io/catthehacker/ubuntu:act-latest";
        "ubuntu-20.04" = "ghcr.io/catthehacker/ubuntu:act-20.04";
        "ubuntu-18.04" = "ghcr.io/catthehacker/ubuntu:act-18.04";
      };
    };
  };
}
