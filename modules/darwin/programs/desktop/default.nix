{
  config,
  lib,
  pkgs,
  ...
}:

let
  appsDir = "${config.home.homeDirectory}/${config.targets.darwin.copyApps.directory}";
  lsregister = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister";

in
{
  targets.darwin.copyApps.enable = true;
  targets.darwin.linkApps.enable = false;

  # Wrapped apps exec into /nix/store bundles, whose duplicate registrations make `open` spawn a second instance
  home.activation.pruneLaunchServices = lib.hm.dag.entryAfter [ "copyApps" ] ''
    mapfile -t storeApps < <(
      ${lsregister} -dump Bundle \
        | ${pkgs.gnused}/bin/sed -nE 's|^path: +(/nix/store/.*) \(0x[0-9a-f]+\)$|\1|p'
    )
    if (( ''${#storeApps[@]} )); then
      run ${lsregister} -u "''${storeApps[@]}"
    fi
    run ${lsregister} -f "${appsDir}"/*.app
  '';

  targets.darwin.defaults = {
    NSGlobalDomain.AppleLanguages = [
      "en-US"
      "ko-KR"
    ];
    NSGlobalDomain.AppleLocale = "en_US";

    "com.apple.desktopservices" = {
      DSDontWriteNetworkStores = true;
      DSDontWriteUSBStores = true;
    };
  };

  targets.darwin.keybindings = {
    "₩" = [
      "insertText:"
      "`"
    ];
  };

  programs.desktoppr = {
    enable = true;
    settings = {
      picture = "/System/Library/Desktop Pictures/Solid Colors/Black.png";
      color = "000000";
      scale = "fill";
    };
  };
}
