{ config, pkgs, ... }:

{
  imports = [
    ./aws-vault.nix
    ./awscli.nix
  ];
}
