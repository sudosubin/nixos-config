{ config, pkgs, lib, ... }:
with lib;

let
  cfg = config.programs._1password;

  makeWrapperFHSEnvironment = pkgs.runCommand "wrap-fhs-environment.sh" { } ''
    substitute ${./wrap-fhs-environment.sh} $out \
      --replace @shell@ ${pkgs.bash}/bin/bash \
      --replace @sha256sum@ ${pkgs.coreutils}/bin/sha256sum
  '';

  package =
    if cfg.enableFHSEnvironment
    then
      cfg.package.overrideAttrs
        (attrs: {
          nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];

          postInstall = ''
            ${attrs.postInstall or ""}
            source ${makeWrapperFHSEnvironment}
            wrapFHSEnvironment "$out/bin/op" "/usr/local/bin/op"
          '';

          doInstallCheck = false;
        })
    else cfg.package;

in
{
  options.programs._1password = {
    enable = mkEnableOption "1password";

    package = mkPackageOption pkgs "_1password" { };

    enableFHSEnvironment = mkOption {
      type = types.bool;
      default = false;
      description = "Enable /usr/local/bin/op binary to connect with 1Password app.";
    };
  };

  config = mkMerge [
    (mkIf cfg.enable {
      home.packages = [ package ];
    })
  ];
}
