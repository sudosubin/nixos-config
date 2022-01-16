{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    gnupg
  ];

  programs.gpg = {
    enable = true;
    publicKeys = [
      {
        source = ./gpg/public.key;
        trust = "ultimate";
      }
    ];
  };
}
