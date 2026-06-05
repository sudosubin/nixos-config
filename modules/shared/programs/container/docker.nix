{
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;

in
{
  home.packages = lib.optionals isLinux (
    with pkgs;
    [
      docker
      docker-buildx
      docker-compose
      docker-credential-helpers
    ]
  );

  services.orbstack = lib.mkIf isDarwin {
    enable = true;

    package = pkgs.orbstack.overrideAttrs (old: {
      postInstall = (old.postInstall or "") + ''
        rm -f "$out/bin/kubectl"
      '';
    });

    config = {
      SUAutomaticallyUpdate = 0;
      SUEnableAutomaticChecks = 0;
      SUScheduledCheckInterval = 0;
      SUSendProfileInfo = 0;
    };
  };
}
