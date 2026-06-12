{
  config,
  pkgs,
  ...
}:

{
  home.sessionVariables = {
    NIX_ACTIVATE_ROOT = "${config.home.homeDirectory}/Code/github.com/sudosubin/nixos-flakes";
  };

  home.packages = with pkgs; [
    nixd
    nixfmt
    nixVersions.stable
    nix-activate
  ];
}
