{ config, pkgs, ... }:

{
  imports = [
    ./bpython.nix
    ./pipenv.nix
    ./poetry.nix
    ./python.nix
  ];

  home.packages = with pkgs; [ rye ];
}
