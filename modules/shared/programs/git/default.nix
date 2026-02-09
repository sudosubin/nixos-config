{ pkgs, ... }:

{
  imports = [
    ./delta.nix
    ./gh.nix
    ./git.nix
  ];

  home.packages = with pkgs; [
    gitbutler
    git-spr
    git-who
  ];
}
