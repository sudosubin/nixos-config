{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    awscli2
  ];

  home.file = {
    ".aws/config".text = ''
      [default]
      region = ap-northeast-2
    '';
  };
}
