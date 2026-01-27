{
  pkgs,
  lib,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;

in
{
  home.packages =
    [ ]
    ++ lib.optionals isLinux (
      with pkgs;
      [
        docker
        docker-buildx
        docker-compose
        docker-credential-helpers
      ]
    )
    ++ lib.optionals isDarwin (
      with pkgs;
      [
        orbstack
      ]
    );
}
