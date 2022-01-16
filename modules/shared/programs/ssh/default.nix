{ config, pkgs, ... }:

{
  programs.ssh = {
    enable = true;
    extraConfig = ''
      AddressFamily inet
      StrictHostKeyChecking no
    '';
  };
}
