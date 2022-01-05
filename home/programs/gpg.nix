{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    gnupg
  ];

  programs.gpg = {
    enable = true;
    publicKeys = [
      {
        source = ../files/gpg/public.key;
        trust = "ultimate";
      }
    ];
  };
}
