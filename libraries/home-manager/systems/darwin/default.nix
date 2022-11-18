{ config, pkgs, lib, ... }:

let
  apps = pkgs.buildEnv {
    name = "home-manager-applications";
    paths = config.home.packages;
    pathsToLink = "/Applications";
  };

in
{
  # Enable spotlight application
  home.activation.copyApplications = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    BASE_DIR="${config.home.homeDirectory}/Applications/Home Manager Apps"
    if [ -d "$BASE_DIR" ]; then
      rm -rf "$BASE_DIR"
    fi

    mkdir -p "$BASE_DIR"
    for app_file in ${apps}/Applications/*; do
      target="$BASE_DIR/$(basename "$app_file")"
      $DRY_RUN_CMD cp ''$VERBOSE_ARG -fHRL "$app_file" "$BASE_DIR"
      $DRY_RUN_CMD chmod ''$VERBOSE_ARG -R +w "$target"
    done
  '';

  disabledModules = [ "targets/darwin/linkapps.nix" ];
}
